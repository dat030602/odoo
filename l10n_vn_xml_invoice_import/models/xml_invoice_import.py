# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero
from ..services.xml_parser import VietnameseInvoiceParser
from datetime import datetime


class XmlInvoiceImport(models.Model):
    """Main model for storing imported XML invoice data."""

    _name = "xml.invoice.import"
    _description = "XML Invoice Import"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "invoice_date desc, id desc"

    # State
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review", "Review"),
            ("move_created", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        default="draft",
        tracking=True,
        required=True,
    )

    # Checksums for duplicate protection
    raw_file_checksum = fields.Char(string="Raw File Checksum", readonly=True, copy=False, index=True)
    business_checksum = fields.Char(string="Business Checksum", readonly=True, copy=False, index=True)

    # Invoice Header (readonly - imported from XML)
    version = fields.Char(string="Version", readonly=True)
    invoice_number = fields.Char(string="Invoice Number", readonly=True, tracking=True)
    invoice_sequence = fields.Char(string="Invoice Sequence", readonly=True)
    invoice_series = fields.Char(string="Invoice Series", readonly=True)
    invoice_date = fields.Date(string="Invoice Date", readonly=True, tracking=True)
    is_main_invoice = fields.Boolean(string="Is Main Invoice", readonly=True)
    currency_rate = fields.Float(string="Currency Rate", readonly=True, digits=(16, 4))
    payment_method = fields.Char(string="Payment Method", readonly=True)
    seller_tax_code = fields.Char(string="Seller Tax Code", readonly=True)

    # Seller Information (readonly - imported from XML)
    seller_name = fields.Char(string="Seller Name", readonly=True)
    seller_vat = fields.Char(string="Seller VAT", readonly=True)
    seller_address = fields.Text(string="Seller Address", readonly=True)
    seller_phone = fields.Char(string="Seller Phone", readonly=True)
    seller_bank_account = fields.Char(string="Seller Bank Account", readonly=True)
    seller_bank_name = fields.Char(string="Seller Bank Name", readonly=True)
    seller_partner_id = fields.Many2one("res.partner", string="Seller Partner", compute="_compute_partners", store=True)

    # Buyer Information (readonly - imported from XML)
    buyer_name = fields.Char(string="Buyer Name", readonly=True)
    buyer_vat = fields.Char(string="Buyer VAT", readonly=True)
    buyer_address = fields.Text(string="Buyer Address", readonly=True)
    buyer_phone = fields.Char(string="Buyer Phone", readonly=True)
    buyer_code = fields.Char(string="Buyer Code", readonly=True)
    buyer_partner_id = fields.Many2one("res.partner", string="Buyer Partner", compute="_compute_partners", store=True)
    einvoice_type = fields.Selection(
        [
            ("in", "Vendor Bill"),
            ("out", "Customer Invoice"),
        ],
        string="E-Invoice Type",
        readonly=True,
        default="in",
        compute="_compute_invoice_type",
        store=True,
    )
    invoice_type = fields.Char(
        string="Invoice Type",
        readonly=True,
    )

    @api.depends("buyer_vat", "company_id.vat")
    def _compute_invoice_type(self):
        for record in self:
            if record.buyer_vat and record.company_id.vat and record.buyer_vat != record.company_id.vat:
                record.einvoice_type = "out"
            else:
                record.einvoice_type = "in"

    # Totals (readonly - imported from XML)
    price_subtotal = fields.Monetary(string="Price Subtotal", readonly=True, currency_field="currency_id")
    price_tax = fields.Monetary(string="Price Tax", readonly=True, currency_field="currency_id")
    price_total = fields.Monetary(string="Total Amount", readonly=True, currency_field="currency_id")
    price_total_text = fields.Text(string="Price Total Text", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)

    # Raw Invoice Lines (readonly - exact XML values)
    raw_line_ids = fields.One2many(
        "xml.invoice.raw.line",
        "xml_import_id",
        string="Raw Invoice Lines",
        readonly=True,
    )

    # Staging Invoice Lines (editable after first confirm)
    invoice_line_ids = fields.One2many("xml.invoice.line", "xml_import_id", string="Invoice Lines")

    # Tax totals computed field
    tax_totals = fields.Json(compute="_compute_tax_totals", string="Tax Totals")

    # Company
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    # Note
    note = fields.Text(string="Notes")

    @api.constrains("invoice_number", "invoice_series", "invoice_date", "company_id", "state")
    def _check_duplicate_invoice(self):
        """Check for duplicate invoices based on series, number, date, and company."""
        for record in self:
            if not (record.invoice_series and record.invoice_number and record.invoice_date):
                continue  # Skip if any key field is missing

            existing = self.search(
                [
                    ("id", "!=", record.id),
                    ("invoice_series", "=", record.invoice_series),
                    ("invoice_number", "=", record.invoice_number),
                    ("invoice_date", "=", record.invoice_date),
                    ("company_id", "=", record.company_id.id),
                    ("state", "!=", "cancelled"),
                ],
                limit=1,
            )
            if existing:
                raise ValidationError(
                    _(
                        "Duplicate invoice detected: Series '%s', Number '%s', Date '%s' already exists for company '%s'."
                    )
                    % (
                        record.invoice_series,
                        record.invoice_number,
                        record.invoice_date,
                        record.company_id.name,
                    )
                )

    @api.depends("invoice_number", "invoice_series", "invoice_date")
    def _compute_display_name(self):
        for record in self:
            name = ""
            if record.invoice_series:
                name += record.invoice_series
            if record.invoice_number:
                if name:
                    name += " - "
                name += record.invoice_number
            if record.invoice_date:
                if name:
                    name += " - "
                name += record.invoice_date.strftime("%Y-%m-%d")
            record.display_name = name

    @api.depends("seller_vat", "buyer_vat")
    def _compute_partners(self):
        """Auto-detect partners based on VAT."""
        for record in self:
            # Find seller partner by VAT
            if record.seller_vat:
                seller_partner = self.env["res.partner"].search(
                    [
                        ("vat", "=", record.seller_vat),
                        ("company_id", "in", [record.company_id.id, False]),
                    ],
                    limit=1,
                )
                record.seller_partner_id = (
                    seller_partner.id if seller_partner else False
                )
            else:
                record.seller_partner_id = False

            # Find buyer partner by VAT
            if record.buyer_vat:
                buyer_partner = self.env["res.partner"].search(
                    [
                        ("vat", "=", record.buyer_vat),
                        ("company_id", "in", [record.company_id.id, False]),
                    ],
                    limit=1,
                )
                record.buyer_partner_id = buyer_partner.id if buyer_partner else False
            else:
                record.buyer_partner_id = False

    def _get_priced_lines(self):
        return self.invoice_line_ids

    @api.depends_context('lang')
    @api.depends(
        "invoice_line_ids.price_subtotal",
        "invoice_line_ids.price_tax",
        "invoice_line_ids.price_total",
        "currency_id",
        "company_id",
    )
    def _compute_tax_totals(self):
        AccountTax = self.env['account.tax']
        for rec in self:
            invoice_lines = rec._get_priced_lines()
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in invoice_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, rec.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, rec.company_id)
            rec.tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=rec.currency_id or rec.company_id.currency_id,
                company=rec.company_id,
            )

    def action_create_seller_partner(self):
        """Create seller partner from imported data."""
        self.ensure_one()
        if self.seller_partner_id:
            raise UserError(_("Seller partner already exists."))

        partner_vals = {
            "name": self.seller_name or _("Unknown Seller"),
            "vat": self.seller_vat or False,
            "street": self.seller_address or False,
            "supplier_rank": 1,
            "company_id": self.company_id.id,
        }

        partner = self.env["res.partner"].create(partner_vals)
        self.seller_partner_id = partner.id
        self.message_post(body=_("Created seller partner: %s") % partner.name)

        return {
            "type": "ir.actions.act_window",
            "name": _("Seller Partner"),
            "res_model": "res.partner",
            "res_id": partner.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_create_buyer_partner(self):
        """Create buyer partner from imported data."""
        self.ensure_one()
        if self.buyer_partner_id:
            raise UserError(_("Buyer partner already exists."))

        partner_vals = {
            "name": self.buyer_name or _("Unknown Buyer"),
            "vat": self.buyer_vat or False,
            "street": self.buyer_address or False,
            "customer_rank": 1,
            "company_id": self.company_id.id,
        }

        partner = self.env["res.partner"].create(partner_vals)
        self.buyer_partner_id = partner.id
        self.message_post(body=_("Created buyer partner: %s") % partner.name)

        return {
            "type": "ir.actions.act_window",
            "name": _("Buyer Partner"),
            "res_model": "res.partner",
            "res_id": partner.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_confirm(self):
        """First confirmation: Generate invoice lines from raw lines."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only draft invoices can be confirmed."))

        # Generate invoice lines from raw lines
        self._generate_invoice_lines()
        self.note = "\n".join(self.raw_line_ids.filtered(lambda line: line.type == "4").mapped("name"))

        # Move to review state
        self.state = "review"
        self.message_post(body=_("Invoice confirmed and lines generated."))

    def _generate_invoice_lines(self):
        """Generate invoice lines from raw lines with product matching."""
        self.ensure_one()

        # Clear existing invoice lines
        self.invoice_line_ids.unlink()

        # Get product matching threshold from system parameters
        threshold = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("l10n_vn_xml_invoice_import.product_match_threshold", default="80")
        )
        for raw_line in self.raw_line_ids.filtered(lambda line: line.type != "4"):
            # Try fuzzy product matching
            product_id = self._match_product(raw_line.name, threshold)

            # Find tax by percentage
            tax_ids = self._find_tax(raw_line.tax_percent)

            # Create invoice line
            self.env["xml.invoice.line"].create(
                {
                    "xml_import_id": self.id,
                    "product_id": product_id.id if product_id else False,
                    "name": raw_line.name,
                    "quantity": raw_line.quantity,
                    "price_unit": raw_line.price_unit,
                    "tax_ids": [(6, 0, tax_ids.ids)] if tax_ids else False,
                    "price_subtotal": raw_line.price_subtotal,
                    "price_tax": raw_line.price_tax,
                    "price_total": raw_line.price_total,
                }
            )

    def _match_product(self, name, threshold=80):
        """Match product by name using fuzzy search."""
        if not name:
            return self.env["product.product"]

        try:
            from rapidfuzz import fuzz, process

            # Search all products
            products = self.env["product.product"].search(
                [("company_id", "in", [self.company_id.id, False])]
            )

            if not products:
                return self.env["product.product"]

            # Extract product names
            product_names = [(p.id, p.name or "") for p in products]

            # Find best match
            result = process.extractOne(
                name,
                [(pid, pname) for pid, pname in product_names],
                scorer=fuzz.token_sort_ratio,
            )

            if result and result[1] >= threshold:
                product_id = result[0][0]
                return self.env["product.product"].browse(product_id)

        except ImportError:
            # rapidfuzz not installed, skip fuzzy matching
            pass
        except Exception:
            # Any error in fuzzy matching, skip
            pass

        return self.env["product.product"]

    def _find_tax(self, tax_percent):
        """Find tax by percentage."""
        if not tax_percent or float_is_zero(tax_percent, precision_digits=2):
            return self.env["account.tax"]

        tax = self.env["account.tax"].search(
            [
                ("amount", "=", tax_percent),
                ("type_tax_use", "in", ["sale", "purchase"]),
                ("company_id", "in", [self.company_id.id, False]),
            ],
            limit=1,
        )

        return tax

    def button_draft(self):
        """Set state to draft."""
        self.write({"state": "draft"})
        self.invoice_line_ids.unlink()

    def action_post(self):
        """Open wizard to create account move."""
        self.ensure_one()
        if self.state != "review":
            raise UserError(_("Only review invoices can create account move."))

        if not self.buyer_partner_id:
            raise UserError(_("Please select or create a buyer partner first."))

        if not self.invoice_line_ids:
            raise UserError(_("No invoice lines to create account move."))

        if not self.invoice_line_ids.mapped("product_id"):
            raise UserError(_("Please match products for all invoice lines before posting."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Create Account Move"),
            "res_model": "xml.invoice.create.move.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_xml_import_id": self.id,
                "default_buyer_partner_id": self.buyer_partner_id.id,
            },
        }

    def action_view_move(self):
        """View related account move."""
        self.ensure_one()

        move_id = self.env['account.move'].search([('xml_import_id', '=', self.id)], limit=1)
        if move_id:
            return {
                "type": "ir.actions.act_window",
                "name": _("Account Move"),
                "res_model": "account.move",
                "res_id": move_id.id,
                "view_mode": "form",
                "target": "current",
            }
        return

    def unlink(self):
        """Prevent deletion of finalized imports."""
        for record in self:
            if record.state == "move_created":
                raise UserError(_("Cannot delete invoice import that has already created an account move."))
        return super().unlink()

    def _prepare_import_common_values(self, data):
        return {
            "version": data.get("PBan"),
            "invoice_type": data.get("THDon"),
            "invoice_sequence": data.get("KHMSHDon"),
            "invoice_series": data.get("KHHDon"),
            "invoice_number": data.get("SHDon"),
            "invoice_date": data.get("NLap"),
            "is_main_invoice": data.get("HDCTTChinh"),
            "currency_id": data.get("DVTTe"),
            "currency_rate": self.safe_float(data.get("TGia")),
            "payment_method": data.get("HTTToan"),
            "seller_tax_code": data.get("MSTTCGP"),
        }

    def _prepare_import_payment_values(self, data):
        return {
            "price_subtotal": self.safe_float(data.get("TgTCThue")),
            "price_tax": self.safe_float(data.get("TgTThue")),
            "price_total": self.safe_float(data.get("TgTTTBSo")),
            "price_total_text": data.get("TgTTTBChu"),
        }

    def _prepare_import_seller_values(self, data):
        return {
            "seller_name": data.get("Ten"),
            "seller_vat": data.get("MST"),
            "seller_address": data.get("DChi"),
            "seller_phone": data.get("SDThoai"),
            "seller_bank_account": data.get("STKNHang"),
            "seller_bank_name": data.get("TNHang"),
        }

    def _prepare_import_buyer_values(self, data):
        return {
            "buyer_name": data.get("Ten"),
            "buyer_vat": data.get("MST"),
            "buyer_address": data.get("DChi"),
            "buyer_phone": data.get("SDThoai"),
            "buyer_code": data.get("MKHang"),
        }

    def _prepare_import_invoice_line_values(self, data):
        values = []
        for line in data:
            amount_other = [self.safe_float(item.get("KDLieu", 0)) for item in line.get("TTKhac", {}).get("TTin", [])]
            tax_percent_value = line.get("TSuat")
            if tax_percent_value and isinstance(tax_percent_value, str):
                tax_percent_value = tax_percent_value.replace("%", "").strip()
            values.append({
                "type": line.get("TChat"),
                "name": line.get("THHDVu"),
                "uom_name": line.get("DVTinh"),
                "quantity": self.safe_float(line.get("SLuong")),
                "price_unit": self.safe_float(line.get("DGia")),
                "discount": self.safe_float(line.get("TLCKhau")),
                "price_discount": self.safe_float(line.get("STCKhau")),
                "tax_percent": self.safe_float(tax_percent_value),
                "price_total": self.safe_float(line.get("ThTien")),
                "price_tax": min(amount_other) if amount_other else 0,
                "price_subtotal": max(amount_other) if amount_other else 0,
            })
        return {"invoice_lines": values}

    def _prepare_import_values(self, parsed_data):
        values = {}
        values.update(self._prepare_import_seller_values(parsed_data.get("NBan", {})))
        values.update(self._prepare_import_buyer_values(parsed_data.get("NMua", {})))
        values.update(self._prepare_import_payment_values(parsed_data.get("TToan", {})))
        values.update(self._prepare_import_common_values(parsed_data.get("TTChung", {})))
        return values

    @classmethod
    def safe_float(cls, value, default=0.0):
        """Safely convert value to float."""
        if value is None:
            return default
        try:
            return float(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return default

    def create_from_xml(self, xml_content, filename, company_id=None):
        """
        Create invoice import record from XML content.

        Args:
            xml_content (str or bytes): XML file content
            filename (str): Original filename
            company_id (int): Company ID (optional)

        Returns:
            xml.invoice.import: Created record
        """
        # Parse XML
        values = VietnameseInvoiceParser.parse_xml_content(xml_content)

        # Compute checksums
        raw_checksum = VietnameseInvoiceParser.compute_raw_file_checksum(xml_content)

        line_values = self._prepare_import_invoice_line_values(values.get("HHDVu", []))
        values = self._prepare_import_values(values)

        business_checksum = VietnameseInvoiceParser.compute_business_checksum(
            values.get("invoice_series") or "",
            values.get("invoice_number") or "",
            values.get("invoice_date") or "",
        )

        # Check for duplicates
        existing = self.search(
            [
                ("state", "!=", "cancelled"),
                "|",
                ("raw_file_checksum", "=", raw_checksum),
                ("business_checksum", "=", business_checksum),
            ],
            limit=1,
        )

        if existing:
            raise UserError(
                _("This invoice has already been imported (ID: %s).") % existing.id
            )

        # Parse date
        invoice_date = values.get("invoice_date")
        if invoice_date:
            try:

                # Try dd/mm/YYYY format
                if "/" in str(invoice_date):
                    invoice_date = datetime.strptime(
                        str(invoice_date), "%d/%m/%Y"
                    ).date()
                # Try YYYY-mm-dd format
                elif "-" in str(invoice_date):
                    invoice_date = datetime.strptime(
                        str(invoice_date), "%Y-%m-%d"
                    ).date()
            except Exception:
                invoice_date = False
        else:
            invoice_date = False

        if values.get("currency_id"):
            values["currency_id"] = self.env["res.currency"].with_context(active_test=False).search([
                ("name", "=", values.get("currency_id"))
            ], limit=1).id

        # Create main record
        vals = values
        vals.update({
            "raw_file_checksum": raw_checksum,
            "business_checksum": business_checksum,
            "invoice_date": invoice_date,
            "company_id": company_id or self.env.company.id,
            "currency_id": vals.get("currency_id") if isinstance(vals.get("currency_id"), int) else False,
        })


        record = self.create(vals)

        # Create raw lines
        for line_data in line_values.get("invoice_lines", []):
            line_vals = line_data
            line_vals["xml_import_id"] = record.id
            self.env["xml.invoice.raw.line"].create(line_vals)

        # Attach original XML file
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "res_model": "xml.invoice.import",
                "res_id": record.id,
                "type": "binary",
                "datas": xml_content
                if isinstance(xml_content, bytes)
                else xml_content.encode("utf-8"),
            }
        )

        record.message_post(body=_("XML file imported: %s") % filename, attachment_ids=[attachment.id])

        return record

    def action_cancel(self):
        """Cancel the invoice import."""
        self.ensure_one()
        if self.state == "move_created":
            move = self.env['account.move'].search([('xml_import_id', '=', self.id)], limit=1)
            if move:
                move.button_cancel()
        self.state = "cancelled"
