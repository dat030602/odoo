# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class XmlInvoiceLine(models.Model):
    """Staging invoice lines - editable after first confirm, used to create Account Move."""

    _name = "xml.invoice.line"
    _description = "XML Invoice Line"
    _order = "xml_import_id, id"

    xml_import_id = fields.Many2one(
        "xml.invoice.import",
        string="XML Invoice Import",
        required=True,
        ondelete="cascade",
    )

    # Editable fields for creating Account Move
    product_id = fields.Many2one("product.product", string="Product")
    name = fields.Text(string="Description", required=True)
    quantity = fields.Float(string="Quantity", digits="Product Unit of Measure", required=True)
    price_unit = fields.Monetary(string="Unit Price", required=True, currency_field="currency_id")
    tax_ids = fields.Many2many("account.tax", string="Taxes")

    # Computed fields
    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
    )
    price_tax = fields.Monetary(
        string="Tax Amount",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
    )
    price_total = fields.Monetary(string="Total", compute="_compute_amounts", store=True, currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", string="Currency", related="xml_import_id.currency_id", store=True)

    @api.depends("quantity", "price_unit", "tax_ids")
    def _compute_amounts(self):
        """Compute subtotal, tax, and total amounts."""
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

            # Compute tax amount
            taxes = line.tax_ids.compute_all(
                price_unit=line.price_unit,
                quantity=line.quantity,
                product=line.product_id,
                partner=line.xml_import_id.buyer_partner_id,
            )

            line.price_tax = sum(t.get("amount", 0.0) for t in taxes.get("taxes", []))
            line.price_total = taxes.get(
                "total_included", line.price_subtotal + line.price_tax
            )

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        company = self.xml_import_id.company_id or self.env.company
        base_values = {
            'tax_ids': self.tax_ids,
            'quantity': self.quantity,
            'partner_id': self.xml_import_id.buyer_partner_id,
            'currency_id': self.xml_import_id.currency_id or company.currency_id,
            'name': self.name,
        }
        base_values.update(kwargs)
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(self, **base_values)

    @api.constrains("quantity", "price_unit")
    def _check_positive_values(self):
        """Ensure quantity and price are positive."""
        for line in self:
            if line.quantity < 0:
                raise UserError(_("Quantity cannot be negative."))
            if line.price_unit < 0:
                raise UserError(_("Unit price cannot be negative."))
