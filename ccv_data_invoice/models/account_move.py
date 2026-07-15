from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import unidecode
from rapidfuzz import process
import logging

_logger = logging.getLogger(__name__)

def normalize_name(name):
    """Chuẩn hóa tên sản phẩm (lowercase, bỏ dấu, chuẩn ký tự phân cách)."""
    if not name:
        return ""
    name = name.lower()
    name = unidecode.unidecode(name)  # bỏ dấu
    name = re.sub(r'[\s\*xX\-]+', 'x', name)  # chuẩn hóa x/*/-
    name = re.sub(r'\s+', ' ', name).strip()
    return name


class AccountMove(models.Model):
    _inherit = 'account.move'

    purchase_ids = fields.Many2many('purchase.order', string='Đơn đặt hàng')
    invoice_data_ids = fields.Many2many('invoice.data', string='Hóa đơn điện tử')

    @api.model
    def create(self, vals):
        """Override create để gán invoice vào purchase order nếu có"""
        record = super(AccountMove, self).create(vals)
        
        # Kiểm tra nếu có purchase_ids
        if record.purchase_ids: 
            for purchase in record.purchase_ids:
                # Gán invoice hiện tại vào invoice_ids của purchase order
                purchase.invoice_ids = [(4, record.id)]
        
        return record

    def action_open_update_invoice_info_wizard(self):
        move = self[:1]
        default_date_invoice = False
        if len(self) == 1 and 'date_invoice' in self._fields:
            default_date_invoice = move.date_invoice
        elif len(self) == 1 and 'invoice_date' in self._fields:
            default_date_invoice = move.invoice_date

        return {
            'type': 'ir.actions.act_window',
            'name': _('Cập nhật thông tin hóa đơn'),
            'res_model': 'wz.account.move.update.invoice.info',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ref': move.ref if len(self) == 1 else False,
                'default_series': move.series if len(self) == 1 and 'series' in self._fields else False,
                'default_date_invoice': default_date_invoice,
                'active_model': 'account.move',
                'active_ids': self.ids,
            }
        }
