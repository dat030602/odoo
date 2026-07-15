from odoo import models, fields, api, _

class EditAccountMoveExchangeLineWizard(models.TransientModel):
    _name = 'edit.account.move.exchange.line.wizard'
    _description = 'Dòng Wizard cho Phiếu Điều Chuyển Kho'
    
    wizard_id = fields.Many2one('edit.account.move.exchange.wizard', string="Wizard")
    line_id = fields.Many2one('account.move.line', string="Account Move Line")
    
    # Các trường này giờ đây được điền giá trị bởi default_get, không cần compute
    debit = fields.Monetary (string="Nợ")
    credit = fields.Monetary(string="Có")
    currency_id = fields.Many2one('res.currency', string="Tiền tệ")
    
    account_id = fields.Many2one('account.account', string="Tài Khoản")
    
    @api.onchange('debit', 'credit')
    def _onchange_debit_credit(self):
        for rec in self:
            # Nếu sửa debit thì credit = 0
            if rec.debit:
                rec.credit = 0.0
            # Nếu sửa credit thì debit = 0
            elif rec.credit:
                rec.debit = 0.0
    
    def _prepare_line_vals(self):
        return [1, self.line_id._origin.id, { 'debit': self.debit, 'credit': self.credit}]
