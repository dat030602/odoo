from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    move_name = fields.Char(store=True, compute='_compute_move_name')

    @api.depends('move_id.name')
    def _compute_move_name(self):
        for line in self:
            line.move_name = line.move_id.name


    # def create(self, vals_list):
    #     records = super(AccountMoveLine, self).create(vals_list)
    #     print("vals_list", vals_list)
    #     return records
    
    # def write(self, vals):
    #     res = super(AccountMoveLine, self).write(vals)
    #     for invoice in self:
    #         tax_ids = []
    #         for tax in invoice.tax_ids:
    #             for rep in tax.invoice_repartition_line_ids:
    #                 if rep.repartition_type == 'tax':
    #                     vals = {
    #                         'tax_tag_id': rep.tag_ids.id,
    #                         'amount': tax.amount / 100,
    #                     }
    #                     tax_ids.append(vals)
    #         tax_ids = sorted(tax_ids, key=lambda x: x['amount'])

    #         debit_sum = 0
    #         for line in self.move_id.line_ids:
    #             if invoice.product_id.id == line.product_id.id:
    #                 debit_sum = line.debit
                    
    #         for tax in tax_ids:
                
    #             for line_2 in self.move_id.line_ids:
    #                 if len(line_2.tax_tag_ids) == 1 and not line_2.product_id:
    #                     if line_2.tax_tag_ids.id == tax['tax_tag_id']:
    #                         line_2.debit = debit_sum * tax['amount']
    #                         debit_sum += line_2.debit
    #     return res
    
    @api.constrains('account_id', 'display_type')
    def _check_payable_receivable(self):
        pass

    


    # tax_amount_value = fields.Monetary(inverse='_inverse_tax_amount_value')

    # def _inverse_tax_amount_value(self):
    #     for line in self:
    #         # Cập nhật lại giá trị subtotal và total sau khi sửa thuế
    #         line.price_subtotal = line.price_unit * line.quantity
    #         line.price_total = line.price_subtotal - line.tax_amount_value

    #         tax_lines = line._get_tax_line_for_current()
            
    #         if tax_lines:
    #             total_tax_value = sum([abs(tax_line.balance) for tax_line in tax_lines])
    #             tax_difference = line.tax_amount_value - total_tax_value
    #             for tax_line in tax_lines:
    #                 if tax_line.debit:
    #                     tax_line.debit += tax_difference
    #                 if tax_line.credit:
    #                     tax_line.credit += tax_difference
    #                 break

    # def _get_tax_line_for_current(self):
    #     """ Lấy tất cả các dòng thuế cùng loại liên quan đến dòng hiện tại khi sửa tax_amount_value """
    #     self.ensure_one()
    #     # Sử dụng tax_key để lấy các dòng thuế cùng loại
    #     tax_key = self._generate_tax_key(self)
    #     tax_lines = self.move_id.line_ids.filtered(
    #         lambda l: l.display_type == 'tax' and self._generate_tax_key(l) == tax_key
    #     )
    #     return tax_lines

    # def _generate_tax_key(self, line):
    #     """ Tạo tax_key từ các thông tin quan trọng của dòng thuế """
    #     self.ensure_one()
    #     # Tạo tax_key từ thông tin của invoice_line_ids
    #     # Thay thế các trường không có sẵn bằng các thông tin khác như move_id, partner_id, tax_ids...
        
    #     tax_key = f"{line.move_id.id}_{line.partner_id.id}_{line.tax_line_id.id if line.tax_line_id else (line.tax_ids[0].id if line.tax_ids else 'no_tax_line')}"
        
    #     # Nếu có expense_id hoặc các thông tin khác thì thêm vào key
    #     expense_id = line.tax_key.get('expense_id', False)
    #     if expense_id:
    #         tax_key += f'_{expense_id}'

    #     return tax_key


