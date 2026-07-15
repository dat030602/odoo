from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)


class stock_picking_type(models.Model):
    _inherit = 'mrp.production'

    plan_mrp_id = fields.Many2one('ccv.mrp.plan.export')
    plan_mrp_line_id = fields.Many2one('ccv.sale.plan.export.line2')
    sale_ids = fields.Many2many('sale.order', string='Đơn bán hàng')
    partner_ids = fields.Many2many('res.partner', string='Khách hàng')
    
    @api.onchange('sale_ids')
    def _onchange_sale_ids(self):
        for rec in self:
            rec.partner_ids = rec.sale_ids.mapped('partner_id')
