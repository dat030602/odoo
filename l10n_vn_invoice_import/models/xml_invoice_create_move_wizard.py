# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class XmlInvoiceCreateMoveWizard(models.TransientModel):
    """Wizard for creating Account Move from review invoice import."""

    _name = "xml.invoice.create.move.wizard"
    _description = "XML Invoice Create Move Wizard"

    xml_import_id = fields.Many2one("xml.invoice.import", string="XML Invoice Import", required=True, readonly=True)
    buyer_partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    move_type = fields.Selection(
        [
            ("out_invoice", "Customer Invoice"),
            ("in_invoice", "Vendor Bill"),
            ("out_refund", "Customer Credit Note"),
            ("in_refund", "Vendor Credit Note"),
        ],
        string="Move Type",
        required=True,
        default="in_invoice",
    )
    journal_id = fields.Many2one("account.journal", string="Journal", required=True)
    invoice_date = fields.Date(string="Invoice Date", required=True)

    @api.onchange("move_type")
    def _onchange_move_type(self):
        """Set default journal based on move type."""
        if self.move_type:
            if self.move_type in ("out_invoice", "out_refund"):
                journal_type = "sale"
            else:
                journal_type = "purchase"

            journal = self.env["account.journal"].search(
                [("type", "=", journal_type), ("company_id", "=", self.env.company.id)],
                limit=1,
            )
            self.journal_id = journal.id if journal else False

    @api.onchange("xml_import_id")
    def _onchange_xml_import_id(self):
        """Set default values from XML import."""
        if self.xml_import_id:
            self.buyer_partner_id = self.xml_import_id.buyer_partner_id.id
            self.invoice_date = self.xml_import_id.invoice_date
            self._onchange_move_type()

    def action_create_move(self):
        """Create Account Move from invoice import."""
        self.ensure_one()

        if not self.xml_import_id.invoice_line_ids:
            raise UserError(_("No invoice lines to create move from."))

        # Prepare move lines
        move_lines = []
        for line in self.xml_import_id.invoice_line_ids:
            move_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": line.product_id.id if line.product_id else False,
                        "name": line.name,
                        "quantity": line.quantity,
                        "price_unit": line.price_unit,
                        "tax_ids": [(6, 0, line.tax_ids.ids)]
                        if line.tax_ids
                        else False,
                    },
                )
            )

        # Create account move
        move_vals = {
            "move_type": self.move_type,
            "partner_id": self.buyer_partner_id.id,
            "journal_id": self.journal_id.id,
            "invoice_date": self.invoice_date,
            "invoice_line_ids": move_lines,
            "xml_import_id": self.xml_import_id.id,
        }

        move = self.env["account.move"].create(move_vals)

        # Update XML import record
        self.xml_import_id.state = "move_created"

        return {
            "type": "ir.actions.act_window",
            "name": _("Account Move"),
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "current",
        }
