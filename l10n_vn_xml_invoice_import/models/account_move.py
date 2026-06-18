# -*- coding: utf-8 -*-

from odoo import models, fields, _


class AccountMove(models.Model):
    """Inherit Account Move to add XML import reference."""

    _inherit = "account.move"

    invoice_number = fields.Char(string="Invoice Number", related="xml_import_id.invoice_number", readonly=True)
    invoice_series = fields.Char(string="Invoice Series", related="xml_import_id.invoice_series", readonly=True)

    xml_import_id = fields.Many2one("xml.invoice.import", string="XML Invoice Import", readonly=True, copy=False)

    def action_view_xml_import(self):
        """View related XML invoice import."""
        self.ensure_one()
        if not self.xml_import_id:
            return {}

        return {
            "type": "ir.actions.act_window",
            "name": _("XML Invoice Import"),
            "res_model": "xml.invoice.import",
            "res_id": self.xml_import_id.id,
            "view_mode": "form",
            "target": "current",
        }
