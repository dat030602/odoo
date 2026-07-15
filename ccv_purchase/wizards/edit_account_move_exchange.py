from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime
import logging

_logger  = logging.getLogger(__name__)

class EditAccountMoveExchangeWizard(models.TransientModel):
    _name = 'edit.account.move.exchange.wizard'
    _description = 'Wizard to edit account move exchange'

    account_move_id = fields.Many2one('account.move', string="Account Move")
    line_ids = fields.One2many('edit.account.move.exchange.line.wizard', 'wizard_id', string="Adjustment Lines")
    exchange_rate = fields.Float(string="Tỷ giá", digits=(16, 3))
    
    def _check_is_exchange(self, account_move_id):
        account_move_id.sudo().env['account.full.reconcile'].flush_model(['exchange_move_id'])
        account_move_id.sudo().env['account.partial.reconcile'].flush_model(['exchange_move_id'])
        account_move_id.sudo()._cr.execute(
            """
                SELECT DISTINCT sub.exchange_move_id
                FROM (
                    SELECT exchange_move_id
                    FROM account_full_reconcile
                    WHERE exchange_move_id IN %s

                    UNION ALL

                    SELECT exchange_move_id
                    FROM account_partial_reconcile
                    WHERE exchange_move_id IN %s
                ) AS sub
            """,
            [tuple(account_move_id.sudo().ids), tuple(account_move_id.sudo().ids)],
        )
        exchange_move_ids = set([row[0] for row in account_move_id.sudo()._cr.fetchall()])
        if account_move_id.id not in exchange_move_ids:
            raise UserError(_("Chỉ có thể điều chỉnh các bút toán điều chuyển (exchange)."))

    @api.model
    def default_get(self, fields_list):
        """Lấy giá trị mặc định khi tạo wizard"""
        res = super().default_get(fields_list)
        
        # Lấy account_move_id từ context
        account_move_id = self.env.context.get('default_account_move_id')
        if account_move_id:
            account_move = self.env['account.move'].browse(account_move_id)
            self._check_is_exchange(account_move)
            res['account_move_id'] = account_move_id
            
            # Tạo các dòng line_ids từ account move lines
            line_vals = []
            for line in account_move.line_ids:
                line_vals.append((0, 0, {
                    'line_id': line.id,
                    'debit': line.debit,
                    'credit': line.credit,
                    'currency_id': line.currency_id.id if line.currency_id else False,
                    'account_id': line.account_id.id if line.account_id else False,
                }))
            res['line_ids'] = line_vals
            
            # Lấy tỷ giá mặc định từ account move
            if account_move.currency_id and account_move.currency_id != account_move.company_id.currency_id:
                res['exchange_rate'] = account_move.currency_id.rate or 1.0
        
        return res

    def action_confirm(self):
        """Cập nhật account move lines và amount trong account_partial_reconcile bằng SQL"""
        # Check tổng Debit = Credit trước khi xác nhận
        total_debit = sum([line.debit or 0 for line in self.line_ids])
        total_credit = sum([line.credit or 0 for line in self.line_ids])
        if round(total_debit, 2) != round(total_credit, 2) and total_debit != 0 and total_credit != 0:
            raise UserError("Tổng số tiền Nợ (%s) phải bằng tổng số tiền Có (%s). Vui lòng kiểm tra lại!" % (total_debit, total_credit))
        for line in self.line_ids:
            # Cập nhật debit, credit, account_id, balance cho account move line
            balance = (line.debit or 0) - (line.credit or 0)
            self._cr.execute("""
                UPDATE account_move_line 
                SET debit = %s, credit = %s, account_id = %s, balance = %s
                WHERE id = %s
            """, (
                line.debit, 
                line.credit, 
                line.account_id.id if line.account_id else None, 
                balance,
                line.line_id.id
            ))
            
        # Nếu có amount mới, cập nhật vào account_partial_reconcile
        # Đầu tiên, lấy ra các id của account_partial_reconcile liên quan đến line.line_id.id
        self._cr.execute("""
            SELECT part.id
            FROM account_partial_reconcile part
            JOIN account_move_line credit_line ON credit_line.id = part.credit_move_id
            WHERE credit_line.move_id = %s OR part.debit_move_id = %s

            UNION ALL

            SELECT part.id
            FROM account_partial_reconcile part
            JOIN account_move_line debit_line ON debit_line.id = part.debit_move_id
            WHERE debit_line.move_id = %s OR part.credit_move_id = %s
        """, (
            self.account_move_id.id, self.account_move_id.id,
            self.account_move_id.id, self.account_move_id.id
        ))
        partial_ids = [row[0] for row in self._cr.fetchall()]
        if partial_ids:
            # Sau đó update các bản ghi này
            self._cr.execute("""
                UPDATE account_partial_reconcile
                SET debit_amount_currency = 0,
                    credit_amount_currency = 0,
                    amount = %s
                WHERE id = ANY(%s)
            """, (
                total_debit,
                partial_ids
            ))
        # Commit thay đổi
        self._cr.commit()
