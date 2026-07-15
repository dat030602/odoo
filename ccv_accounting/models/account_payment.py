from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    # def action_reconcile_payment(self):
    #     for payment in self:
    #         if payment.sale_id:
    #             sale_order = payment.sale_id
    #             invoices = sale_order.invoice_ids.filtered(lambda inv: inv.state == 'posted' and inv.payment_state != 'paid')
    #             if not invoices:
    #                 raise UserError("Không tìm thấy hóa đơn cần đối soát cho đơn hàng này!")
    #             invoice_lines = invoices.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.amount_residual > 0)
    #             payment_lines = payment.move_id.line_ids.filtered(lambda line: line.account_id.reconcile and line.amount_residual > 0)
    #             if invoice_lines and payment_lines:
    #                 (invoice_lines + payment_lines).reconcile()
    #             payment.write({'narration': "Đối soát thành công với đơn hàng %s" % sale_order.name})

    # def action_post(self):
    #     res = super(AccountPayment,self).action_post()
    #     self.action_reconcile_payment()
    #     return res

    @api.onchange('payment_type','partner_id','sale_id','sale_ids')
    def onchange_payment_type(self):
        for res in self:
            if res.payment_type == 'inbound':
                ref = 'Thu tiền bán hàng từ '
                if res.partner_id:
                    ref += '%s ' % res.partner_id.name
                ref += '- TT đơn hàng '
                if res.sale_id:
                    ref += '%s' % res.sale_id.name
                elif res.sale_ids:
                    ref += '%s' % ', '.join(res.sale_ids.mapped('name'))
                res.ref = ref
            if res.payment_type == 'outbound':
                res.ref = 'Công ty CCV'
                
    @api.model
    def create(self, values):
        if values.get('payment_type') == 'inbound':
            ref = 'Thu tiền bán hàng từ '
            
            # Thêm tên đối tác nếu có
            if values.get('partner_id'):
                partner = self.env['res.partner'].sudo().browse(int(values['partner_id']))
                ref += '%s ' % partner.name

            ref += '- TT đơn hàng '

            # Xử lý trường sale_id (Many2one)
            if values.get('sale_id'):
                sale = self.env['sale.order'].sudo().browse(int(values['sale_id']))
                ref += '%s ' % sale.name

            # Xử lý trường sale_ids (Many2many) với command 6 và 4
            elif values.get('sale_ids'):
                sale_ids_data = values['sale_ids']
                sale_ids = set()

                for command in sale_ids_data:
                    if isinstance(command, (list, tuple)):
                        if command[0] == 6:
                            # Ghi đè toàn bộ danh sách
                            sale_ids.update(command[2])
                        elif command[0] == 4:
                            # Thêm 1 ID
                            sale_ids.add(command[1])

                if sale_ids:
                    sales = self.env['sale.order'].sudo().browse(list(sale_ids))
                    sale_names = ', '.join(s.name for s in sales)
                    ref += sale_names

            values.update({'ref': ref})

        return super(AccountPayment, self).create(values)

    
