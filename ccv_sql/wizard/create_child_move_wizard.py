# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta

class CreateChildMoveWizard(models.TransientModel):
    _name = 'ccv.create.child.move.wizard'
    _description = 'Tạo Bút Toán công nợ (Nợ/Có)'

    move_type = fields.Selection([
        ('debit', 'Tạo bút toán nợ'),
        ('credit', 'Tạo bút toán có'),
    ], string='Loại bút toán', required=True)
    
    date_from = fields.Date(string="Từ ngày", required=True)
    date_to = fields.Date(string="Đến ngày", default=fields.Date.context_today, required=True)
    
    account_13111_id = fields.Many2one('account.account', string="Tài khoản", required=True)
    opposite_account_id = fields.Many2one('account.account', string="Tài khoản đối ứng", required=True)
    journal_id = fields.Many2one('account.journal', string="Sổ nhật ký", required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        last_month_end = date.today().replace(day=1) - relativedelta(days=1)
        res['date_from'] = last_month_end
        
        acc_13111 = self.env['account.account'].search([('code', '=', '13111')], limit=1)
        if acc_13111:
            res['account_13111_id'] = acc_13111.id
            
        journal = self.env['account.journal'].search([('name', 'ilike', 'Hoạt động khác')], limit=1)
        if not journal:
            journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        if journal:
            res['journal_id'] = journal.id
        
        move_type = self.env.context.get('default_move_type', 'debit')
        res['move_type'] = move_type
        if move_type == 'debit':
            opp_acc = self.env['account.account'].search([('code', '=', '7111')], limit=1)
            if opp_acc:
                res['opposite_account_id'] = opp_acc.id
        else:
            opp_acc = self.env['account.account'].search([('code', '=', '8111')], limit=1)
            if opp_acc:
                res['opposite_account_id'] = opp_acc.id
        return res

    def action_create_moves(self):
        self.ensure_one()
        
        AlphaReport = self.env['alpha.report'].sudo()
        proxy = AlphaReport.create({
            'type': 'chi_tiet_cong_no_phai_thu',
            'account_id': self.account_13111_id.id,
            'name': 'Báo cáo chi tiết công nợ phải thu (Tự động)',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_type': 'is_all_partner',
            'voter_id': self.env.user.id,
        })
        
        proxy.report_chi_tiet_cong_no_phai_thu()
        
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.date_to,
            'invoice_date': self.date_to,
            'invoice_date_due': self.date_to,
            'ref': "Bút toán xử lý chênh lệch công nợ tổng hợp",
            'line_ids': []
        }
        
        # Lấy dòng cuối cùng (số dư cuối cùng) của mỗi đối tác
        final_lines_by_partner = {}
        # Sắp xếp theo id (hoặc date) để đảm bảo luôn lấy đúng dòng được insert cuối cùng (chốt cuối kỳ)
        sorted_lines = proxy.line3_ids.sorted(key=lambda l: l.id)
        for line in sorted_lines:
            if not line.partner_id:
                continue
            # Vì đã sắp xếp, dòng cuối cùng của mỗi partner sẽ là số dư chốt cuối kỳ.
            final_lines_by_partner[line.partner_id.id] = line
            
        has_lines = False
        for partner_id, line in final_lines_by_partner.items():
            amount = 0.0
            if self.move_type == 'debit':
                if line.end_credit > 0 and line.end_credit <= 10000:
                    amount = line.end_credit
            elif self.move_type == 'credit':
                if line.end_debit > 0 and line.end_debit <= 10000:
                    amount = line.end_debit
                    
            if amount > 0:
                has_lines = True
                label = f"Xử lý số dư {'có' if self.move_type == 'debit' else 'nợ'} công nợ nhỏ ({line.partner_id.name})"
                
                if self.move_type == 'debit':
                    # Tạo bút toán nợ: Debit 13111, Credit opposite
                    move_vals['line_ids'].append((0, 0, {
                        'account_id': self.account_13111_id.id,
                        'partner_id': line.partner_id.id,
                        'name': label,
                        'debit': amount,
                        'credit': 0.0,
                        'date_maturity': self.date_to,
                    }))
                    move_vals['line_ids'].append((0, 0, {
                        'account_id': self.opposite_account_id.id,
                        'partner_id': line.partner_id.id,
                        'name': label,
                        'debit': 0.0,
                        'credit': amount,
                        'date_maturity': self.date_to,
                    }))
                else:
                    # Tạo bút toán có: Credit 13111, Debit opposite
                    move_vals['line_ids'].append((0, 0, {
                        'account_id': self.account_13111_id.id,
                        'partner_id': line.partner_id.id,
                        'name': label,
                        'debit': 0.0,
                        'credit': amount,
                        'date_maturity': self.date_to,
                    }))
                    move_vals['line_ids'].append((0, 0, {
                        'account_id': self.opposite_account_id.id,
                        'partner_id': line.partner_id.id,
                        'name': label,
                        'debit': amount,
                        'credit': 0.0,
                        'date_maturity': self.date_to,
                    }))
                
        proxy.unlink()
        
        if not has_lines:
            raise UserError(_("Không tìm thấy khách hàng nào có số dư thỏa mãn điều kiện để tạo bút toán!"))
            
        created_moves = self.env['account.move'].with_context(default_move_type='entry').create([move_vals])
        
        return {
            'name': _('Bút toán công nơ đã tạo'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', created_moves.ids)],
            'target': 'current',
        }
