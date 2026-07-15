from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class account_move_line(models.Model):
    _inherit = "account.move.line"

    def get_reference(self, src_line, cur_line):
        # 1. thông tin ko chạy vào cáo cáo công nợ gồm: Hóa đơn xóa bỏ và HĐ bị thay thế. x
        # 2. thông tin chạy vào cáo cáo công nợ nằm bên Nợ gồm: Dự thảo, Đã phát hành, HĐ thay thế, HĐ bị điều chỉnh tiền
        # 3. thông tin chạy vào cáo cáo công nợ nằm bên Có gồm: HĐ điều chỉnh - Điều chỉnh hàng bán bị trả lại
        # hoặc giảm giá hàng bán (nếu hiện thị âm được thì nằm bên nợ)
        if self.move_id.payment_id:
            return self.move_id.note
        is_credit = src_line.credit != 0

        state = ('','draft','comfirm','created','amount','replace')
        einvoice_status = ('','draft','created','amount')

        move_id = src_line.move_id.sudo()

        sinvoice_ids = move_id.sinvoice_ids.filtered(lambda l: l.einvoice_status != 'canceled' and l.einvoice_status != 'replace' and l.state != 'canceled')

        if not is_credit:
            sinvoice_ids = sinvoice_ids.filtered(lambda l: (l.einvoice_status in einvoice_status  or l.einvoice_status is False) and (l.state in state or l.state is False))
        else:
            sinvoice_ids = sinvoice_ids.filtered(lambda l: l.einvoice_status not in einvoice_status and l.state not in state)
        if sinvoice_ids:
            return ','.join([sinvoice_id.name if sinvoice_id.name else move_id.name for sinvoice_id in sinvoice_ids])
        
        if cur_line.invoice_code and cur_line.invoice_number:
            reference = "%s%s" % (str(cur_line.invoice_code), str(cur_line.invoice_number))
        elif cur_line.invoice_code:
            reference = cur_line.invoice_code
        elif cur_line.invoice_number:
            reference = cur_line.invoice_number
        else:
            reference = cur_line.ref
        return reference
