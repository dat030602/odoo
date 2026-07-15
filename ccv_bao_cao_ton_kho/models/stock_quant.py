from odoo import models, fields
import logging
import datetime

_logger = logging.getLogger(__name__)


class StockReport(models.Model):
    _inherit = "stock.quant"

    def action_create_bien_ban_kiem_ke(self):
        date = datetime.datetime.now()
        name = "Biên bản kiểm kê lúc %s" % date.strftime('%d/%m/%Y %H:%M:%S')
        report_name = "Biên bản kiểm kê"
        
        parent_id = self.env['stock.ccv.report'].search([('type', '=', 'bien_ban_kiem_ke')], limit=1)

        line_data = [(0, 0, {
            'location_id': rec.location_id.id,
            'product_id': rec.product_id.id,
            'quantity': rec.quantity,
            'inventory_quantity': rec.inventory_quantity,
            'diff_quantity': rec.inventory_diff_quantity,
        }) for rec in self]

        report = self.env['stock.ccv.report.line2'].create({
            'name': name,
            'report_name': report_name,
            'date': date,
            'line_ids': line_data,
            'parent_id': parent_id.id if parent_id else False,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Biên bản kiểm kê',
            'res_model': 'stock.ccv.report.line2',
            'view_mode': 'form',
            'res_id': report.id,
            'target': 'current',
        }

