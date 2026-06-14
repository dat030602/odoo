# -*- coding: utf-8 -*-

from odoo import models, fields


class XmlInvoiceRawLine(models.Model):
    """Raw invoice lines - stores original XML values exactly as imported."""

    _name = "xml.invoice.raw.line"
    _description = "XML Invoice Raw Line"
    _order = "xml_import_id, id"

    xml_import_id = fields.Many2one("xml.invoice.import", string="XML Invoice Import", required=True, ondelete="cascade")

    # All fields are readonly - exact XML values
    type = fields.Char(string="Type", readonly=True)
    name = fields.Char(string="Description", readonly=True, required=True)
    uom_name = fields.Char(string="UoM Name", readonly=True)
    quantity = fields.Float(string="Quantity", readonly=True, digits="Product Unit of Measure")
    price_unit = fields.Float(string="Unit Price", readonly=True, digits="Product Price")
    discount = fields.Float(string="Discount Percent", readonly=True, digits="Product Price")
    price_discount = fields.Float(string="Discount Amount", readonly=True, digits="Product Price")
    tax_percent = fields.Float(string="Tax Percent", readonly=True, digits="Account")

    price_subtotal = fields.Float(string="Subtotal", readonly=True, digits="Product Price")
    price_tax = fields.Float(string="Tax Amount", readonly=True, digits="Product Price")
    price_total = fields.Float(string="Total", readonly=True, digits="Product Price")
