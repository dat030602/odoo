# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MisaEinvoicePreviewWizard(models.TransientModel):
    _name = 'misa.einvoice.preview.wizard'
    _description = 'MISA e-Invoice 5-Minute Preview Wizard'

    document_id = fields.Many2one('misa.einvoice.document', string='e-Invoice Document', required=True)
    preview_url = fields.Char(string='Preview URL', required=True)

    def action_open_browser(self):
        """Open preview URL in a new browser tab."""
        self.ensure_one()
        if not self.preview_url:
            raise UserError(_("No preview URL available."))
        return {
            'type': 'ir.actions.act_url',
            'url': self.preview_url,
            'target': 'new',
        }
