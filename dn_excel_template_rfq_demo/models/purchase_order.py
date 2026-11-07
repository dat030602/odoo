# -*- coding: utf-8 -*-
"""Purchase Order model extension for Hetian RFQ Excel Template."""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    x_studio_order_type = fields.Char(
        string='Order Type',
        default='Standard Bulk RFQ',
        help='Order category referenced in Excel template (${fields.x_studio_order_type})',
    )
    x_studio_production_country_1 = fields.Char(
        string='Production Country',
        default='China',
        help='Production origin country (${fields.x_studio_production_country_1})',
    )
    x_customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        help='Customer reference (${fields.x_customer_id.*})',
    )
    conditions = fields.Text(
        string='Terms & Conditions',
        default="""1. Quality Standards: Compliance with Hetian BSK Specification Rev 3.
2. Delivery: F.O.B. Port of Shipment within 30 days of confirmation.
3. Warranty: 12 months comprehensive warranty from delivery date.
4. Inspection: Third-party pre-shipment quality inspection required.""",
        help='Terms and conditions text (${conditions})',
    )
    notes = fields.Html(
        string='Notes',
        related='note',
        readonly=False,
        help='Compatibility alias for note field (${fields.notes})',
    )
    excel_preview_button = fields.Boolean(
        string='Excel Preview Trigger',
        default=True,
    )

    def action_open_excel_template_popup(self):
        """Open the Excel Template Print Preview popup wizard (Visual Builder template)."""
        self.ensure_one()
        hetian_template = self.env['excel.report.template'].search([
            ('model', '=', 'purchase.order'),
            ('config_mode', '=', 'builder'),
            ('name', 'ilike', 'Hetian')
        ], limit=1)
        if not hetian_template:
            hetian_template = self.env['excel.report.template'].search([
                ('model', '=', 'purchase.order'),
                ('name', 'ilike', 'Hetian')
            ], limit=1)

        return {
            'name': _('Print Excel Report - Hetian Summary (Builder)'),
            'type': 'ir.actions.act_window',
            'res_model': 'excel.template.preview.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_template_id': hetian_template.id if hetian_template else False,
            },
        }

    def action_open_excel_python_popup(self):
        """Open the Excel Template Print Preview popup wizard (Python Code template)."""
        self.ensure_one()
        py_template = self.env['excel.report.template'].search([
            ('model', '=', 'purchase.order'),
            ('config_mode', '=', 'code'),
            ('name', 'ilike', 'Hetian')
        ], limit=1)
        if not py_template:
            try:
                from .. import _seed_rfq_demo_data
                _seed_rfq_demo_data(self.env)
                py_template = self.env['excel.report.template'].search([
                    ('model', '=', 'purchase.order'),
                    ('config_mode', '=', 'code')
                ], limit=1)
            except Exception:
                pass

        return {
            'name': _('Print Excel Report - Hetian Python Code Mode'),
            'type': 'ir.actions.act_window',
            'res_model': 'excel.template.preview.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_template_id': py_template.id if py_template else False,
            },
        }
