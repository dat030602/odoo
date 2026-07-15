from odoo import models, fields, api
import datetime
import logging

_logger = logging.getLogger(__name__)


class SaleBonusPriceUnit(models.Model):
    _inherit = "sale.bonus.price.unit"
    
    def action_open_report_wizard(self):
        """
        Mở wizard báo cáo quỹ dự phòng
        """
        if not self:
            # Nếu không có record nào, tạo action mặc định
            return {
                'type': 'ir.actions.act_window',
                'name': 'Báo cáo quỹ dự phòng',
                'res_model': 'bonus.history.report.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_date_from_month': '1',
                    'default_date_from_year': str(datetime.date.today().year),
                    'default_date_to_month': '12',
                    'default_date_to_year': str(datetime.date.today().year),
                }
            }
        
        # Lấy các ngày từ tất cả records được chọn
        date_from_values = self.mapped('date_from')
        date_to_values = self.mapped('date_to')
        
        # Tìm ngày nhỏ nhất và lớn nhất
        valid_date_from = [d for d in date_from_values if d]
        valid_date_to = [d for d in date_to_values if d]
        
        min_date_from = min(valid_date_from) if valid_date_from else None
        max_date_to = max(valid_date_to) if valid_date_to else None
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo quỹ dự phòng',
            'res_model': 'bonus.history.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_date_from_month': str(min_date_from.month) if min_date_from else '1',
                'default_date_from_year': str(min_date_from.year) if min_date_from else str(datetime.date.today().year),
                'default_date_to_month': str(max_date_to.month) if max_date_to else '12',
                'default_date_to_year': str(max_date_to.year) if max_date_to else str(datetime.date.today().year),
            }
        }
