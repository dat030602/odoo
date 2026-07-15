from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    account_id = fields.Many2one("account.account", string="Tài khoản",compute="_compute_account_move")
    account_dest_ids = fields.Many2many("account.account", string="TK Đối ứng",compute="_compute_account_move")
    svl_price_unit = fields.Float("Đơn giá SVL", compute="_compute_account_move")
    analytic_account_id = fields.Many2one('account.analytic.account', string='Mã công trình', compute='_compute_analytic_account_id', store=True, readonly=False)

    @api.depends('picking_id.analytic_account_id')
    def _compute_analytic_account_id(self):
        for move in self:
            if move.picking_id and move.picking_id.analytic_account_id:
                move.analytic_account_id = move.picking_id.analytic_account_id
            else:
                move.analytic_account_id = False
    # nhập lấy nợ
    # xuất lấy có

    def _get_internal_move_lines(self):
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids:
            if move_line._should_exclude_for_valuation():
                continue
            if move_line.location_id._should_be_valued() and move_line.location_dest_id._should_be_valued():
                res |= move_line
        return res

    def _is_internal(self):
        self.ensure_one()
        if self._get_internal_move_lines() and not self._is_dropshipped():
            return True
        return False

    def _compute_account_account_sm(self):
        self.ensure_one()
        account_id = False
        account_dest_id = False
        price_unit = self.product_id.standard_price
        try:
            if self.product_id.type != 'product':
                return account_id, account_dest_id, price_unit
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()

            # _is_in() / _is_out() depend on move_line_ids which are empty in draft state.
            # Fallback to location usage when move_line_ids are not yet created.
            is_in = self._is_in()
            is_out = self._is_out()
            is_internal = self._is_internal()

            if not is_in and not is_out and not is_internal and not self.move_line_ids:
                # Fallback: determine direction from locations directly
                loc_src_usage = self.location_id.usage
                loc_dest_usage = self.location_dest_id.usage
                if loc_src_usage != 'internal' and loc_dest_usage == 'internal':
                    is_in = True
                elif loc_src_usage == 'internal' and loc_dest_usage != 'internal':
                    is_out = True
                elif loc_src_usage == 'internal' and loc_dest_usage == 'internal':
                    is_internal = True

            # credit_account_id, debit_account_id
            if is_in:
                if self._is_returned(valued_type='in'): # xuất
                    account_id = acc_dest
                    account_dest_id = acc_valuation
                else: # nhập
                    account_id = acc_valuation
                    account_dest_id = acc_src
                    if self.product_id.cost_method != 'standard':
                        price_unit = abs(self._get_price_unit())

            elif is_out:
                if self._is_returned(valued_type='out'): # nhập đổi
                    account_id = acc_src
                    account_dest_id = acc_valuation
                    if self.product_id.cost_method != 'standard':
                        price_unit = abs(self._get_price_unit())
                else: # xuất
                    account_id = acc_valuation
                    account_dest_id = acc_dest

            elif is_internal:
                product_accounts = self.product_id._get_product_accounts()
                stock_valuation = product_accounts.get('stock_valuation', False)
                account_id = stock_valuation
                account_dest_id = stock_valuation

            if self.company_id.anglo_saxon_accounting:
                account_id = acc_src
                account_dest_id = acc_dest

        except Exception as e:
            pass
        return account_id, account_dest_id, price_unit


    @api.depends('product_id','location_id','location_dest_id', 'account_move_ids.line_ids.account_id')
    def _compute_account_move(self):
        for rec in self.sudo():
            account_id, account_dest_id, price_unit = rec._compute_account_account_sm()
            rec.account_id = account_id
            rec.svl_price_unit = price_unit

            dest_ids = []
            if account_dest_id:
                dest_ids = [account_dest_id.id if isinstance(account_dest_id, models.Model) else account_dest_id]

            am = rec.account_move_ids.filtered(lambda am: am.state != 'cancel')
            if am and account_id:
                acc_id_val = account_id.id if isinstance(account_id, models.Model) else account_id
                dest_ids = am.mapped('line_ids.account_id').filtered(lambda a: a.id != acc_id_val).ids

            rec.account_dest_ids = [(6, 0, dest_ids or [])]

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        res = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)
        if self.analytic_account_id:
            distribution = {str(self.analytic_account_id.id): 100}
            try:
                # Lấy tài khoản kho (152, 153...) để loại trừ, chỉ gắn mã công trình cho tài khoản đối ứng (2412)
                _, _, _, acc_valuation = self._get_accounting_data_for_valuation()
                
                # Ép kiểu an toàn (đề phòng trường hợp Odoo trả về Object recordset thay vì ID integer)
                acc_val_id = acc_valuation.id if hasattr(acc_valuation, 'id') else acc_valuation
                debit_acc_id = debit_account_id.id if hasattr(debit_account_id, 'id') else debit_account_id
                credit_acc_id = credit_account_id.id if hasattr(credit_account_id, 'id') else credit_account_id

                if 'debit_line_vals' in res and debit_acc_id != acc_val_id:
                    res['debit_line_vals']['analytic_distribution'] = distribution
                if 'credit_line_vals' in res and credit_acc_id != acc_val_id:
                    res['credit_line_vals']['analytic_distribution'] = distribution
            except Exception:
                # Fallback an toàn nếu có lỗi
                if 'debit_line_vals' in res:
                    res['debit_line_vals']['analytic_distribution'] = distribution
        return res
