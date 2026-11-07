# -*- coding: utf-8 -*-
"""Excel Template Print & Preview Popup Wizard."""

import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ExcelTemplatePreviewWizard(models.TransientModel):
    _name = 'excel.template.preview.wizard'
    _description = 'Excel Template Print & Preview Wizard'

    order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order / RFQ',
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        related='order_id.partner_id',
        string='Vendor',
        readonly=True,
    )
    template_id = fields.Many2one(
        'excel.report.template',
        string='Excel Template',
        required=True,
        domain="[('model', '=', 'purchase.order')]",
    )
    filename = fields.Char(string='File Name')
    file_data = fields.Binary(string='Generated Spreadsheet', readonly=True)
    state = fields.Selection(
        [
            ('draft', 'Ready to Generate'),
            ('done', 'Generated Successfully'),
        ],
        string='Status',
        default='draft',
        readonly=True,
    )
    line_count = fields.Integer(
        string='Number of Lines',
        compute='_compute_order_summary',
    )
    total_amount = fields.Monetary(
        string='Total Amount',
        related='order_id.amount_total',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='order_id.currency_id',
    )

    @api.depends('order_id.order_line')
    def _compute_order_summary(self):
        for rec in self:
            rec.line_count = len(rec.order_id.order_line) if rec.order_id else 0

    def action_generate_excel(self):
        """Generate the Excel file in-memory and update wizard state with download ready."""
        self.ensure_one()
        if not self.template_id:
            raise UserError(_("Please select an Excel template."))

        # Render template for this purchase order record
        xlsx_bytes = self.template_id.render_record(self.order_id, strict=True)
        if not xlsx_bytes:
            raise UserError(_("Failed to render Excel template: empty output."))

        clean_po_name = (self.order_id.name or 'RFQ').replace('/', '_').replace('\\', '_')
        fname = f"{clean_po_name}_Hetian_Summary.xlsx"

        self.write({
            'file_data': base64.b64encode(xlsx_bytes),
            'filename': fname,
            'state': 'done',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_print_direct(self):
        """Stream direct browser download via the controller route."""
        self.ensure_one()
        return self.template_id.action_open_download([self.order_id.id])
