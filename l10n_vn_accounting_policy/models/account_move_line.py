from odoo import _, api, models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.constrains('account_id', 'display_type')
    def _check_payable_receivable(self):
        lines_to_check = self.filtered(lambda line: not line.account_id.vn_allow_mixed_usage)
        super(AccountMoveLine, lines_to_check)._check_payable_receivable()

    def _compute_partner_id(self):
        lines_to_compute = self.filtered(lambda line: not (line.move_id.vn_allow_different_partner and line.partner_id))
        super(AccountMoveLine, lines_to_compute)._compute_partner_id()

    def write(self, values):
        if 'partner_id' in values and not self.env.context.get('bypass_line_partner_lock'):
            partner_input = values['partner_id']
            target_partner_id = partner_input.id if isinstance(partner_input, models.BaseModel) else (partner_input or False)
            for move_line in self:
                if move_line.move_id.vn_allow_different_partner:
                    # Nếu hóa đơn đã vào sổ (posted) và cố tình đổi đối tác khác -> Nâng lỗi UserError
                    if move_line.move_id.state == 'posted' and (move_line.partner_id.id or False) != target_partner_id:
                        raise UserError(_("You cannot change the partner on journal items once posted."))
                    # Nếu hóa đơn đang ở trạng thái Nháp (draft) -> HOÀN TOÀN CHO PHÉP (không nâng lỗi)
        return super().write(values)
