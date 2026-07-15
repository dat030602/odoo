from odoo import models, fields, api
from bs4 import BeautifulSoup
import logging
import datetime
import pytz

_logger = logging.getLogger(__name__)

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    has_count_norm = fields.Selection(string='Định mức chỉ may', related="category_id.has_count_norm")
    has_fuel_norm = fields.Selection(string='Định mức xăng dầu', related="category_id.has_fuel_norm")

    def action_create_approval_product_line(self):
        self.ensure_one()
        # Prevent duplicate creations if already created
        existing = self.env['enter.daily.work.output.other'].search([('approval_id', '=', self.id)])
        if existing:
            return

        bom_ids = self.product_line_ids.mapped('product_over_bom_id')
        bom_ids |= self.product_line_ids.mapped('product_over_bom_fuel_id')
        to_create = []
        
        for bom_id in bom_ids:
            product_lines = self.product_line_ids.filtered(lambda l: (l.product_over_bom_id == bom_id or l.product_over_bom_fuel_id == bom_id) and (l.price_over_bom > 0 or l.price_over_bom_fuel > 0))
            if product_lines and bom_id.service_id:
                to_create.append({
                    'date': self.date,
                    'product_id': bom_id.service_id.id,
                    'production_other': 1,
                    'price_unit': -1 * (sum(product_lines.mapped('price_over_bom')) + sum(product_lines.mapped('price_over_bom_fuel'))),
                    'department_ids': [(4, self.department_id.id)],
                    'approval_id': self.id,
                })
        if to_create:
            self.env['enter.daily.work.output.other'].create(to_create)

    def action_approve(self, approver=None):
        res = super().action_approve(approver=approver)
        for rec in self:
            if rec.request_status == 'approved':
                if rec.has_count_norm != 'no' or rec.has_fuel_norm != 'no':
                    rec.sudo().action_create_approval_product_line()
        return res
