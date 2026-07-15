from odoo import fields, models, api, _
from datetime import datetime, date, timedelta
import logging

_logger = logging.getLogger(__name__)


class ccv_sale_plan_export_line(models.Model):
    _name = "ccv.sale.plan.export.line2"
    _inherit = ["ccv.sale.plan.export.line.mixin"]

    bom_id = fields.Many2one(
        "mrp.bom",
        string="Định mức NL",
        domain="""[
        '&',
            ('company_id', '=', 1),
            '&',
                '|',
                    ('product_id','=',product_id),
                    '&',
                        ('product_tmpl_id.product_variant_ids','=',product_id),
                        ('product_id','=',False),
        ('type', '=', 'normal')]""",
    )
    picking_type_id = fields.Many2one("stock.picking.type", string="Nhà máy", domain=[("code", "=", "mrp_operation")])
    parent_state = fields.Selection(string="Loại", selection=[
        ('draft','Nháp'),
        ('confirm','Xác nhận'),
        ('locked','Khóa'),
    ], related="plan_export_id.state")
    plan_export_id = fields.Many2one("ccv.mrp.plan.export")
    mrp_id = fields.Many2one("mrp.production")
    is_highlight = fields.Boolean(compute="_compute_note_highlight")
    
    def _compute_note_highlight(self):
        for rec in self:
            lines = self.env['ccv.sale.plan.export'].search([('date','=',rec.plan_export_id.date),('state','=','locked'),('type','=','summary')]).mapped('line_ids')
            rec.is_highlight = len(lines.filtered(lambda l:l.product_id == rec.product_id and l.note is not False and l.note != '').mapped('note')) != 0

    def _set_qty_delivery(self):
        for rec in self:
            qty_available = 0
            if rec.plan_export_id.location_ids:
                date_only = rec.plan_export_id.date - timedelta(days=1)
                for location_id in rec.plan_export_id.location_ids:
                    qty_available += rec.product_id.with_context(
                        to_date=date_only.strftime("%Y-%m-%d 23:59:59"),
                        location=location_id.id
                    ).qty_available
            else:
                qty_available = rec.product_id.qty_available
            for line in rec.plan_export_id.line_ids.filtered(lambda l:l.product_id == rec.product_id):
                if line.id == rec._origin.id:
                    break
                qty_available -= line.qty_delivery
                if qty_available <= 0:
                    break
            rec.qty_available = qty_available if qty_available > 0 else 0
