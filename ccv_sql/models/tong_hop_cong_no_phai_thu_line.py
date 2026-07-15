# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class CcvTongHopCongNoPhaiThuLine(models.Model):
    _name = 'ccv.tong.hop.cong.no.phai.thu.line'
    _description = 'Dòng Tổng hợp công nợ phải thu'
    _order = 'sequence, id'

    parent_id = fields.Many2one('ccv.tong.hop.cong.no.phai.thu', string="Phiếu", ondelete='cascade', index=True)
    sequence = fields.Integer(string="Thứ tự", default=10)
    team_id = fields.Many2one('crm.team', string="Đội bán hàng")
    partner_id = fields.Many2one('res.partner', string="Khách hàng")
    account_id = fields.Many2one('account.account', string="Tài khoản")
    customer_name = fields.Char(string="Tên khách hàng", default="")
    customer_code = fields.Char(string="Mã khách hàng", default="")
    customer_group = fields.Char(string="Mã nhóm khách hàng", default="")

    start_debit = fields.Float(string="Nợ đầu kỳ", digits=(16, 0))
    start_credit = fields.Float(string="Có đầu kỳ", digits=(16, 0))
    ps_debit = fields.Float(string="PS nợ", digits=(16, 0))
    ps_credit = fields.Float(string="PS có", digits=(16, 0))
    end_debit = fields.Float(string="Nợ cuối kỳ", digits=(16, 0))
    end_credit = fields.Float(string="Có cuối kỳ", digits=(16, 0))

    start_debit_nt = fields.Float(string="Nợ đầu kỳ (NT)", digits=(16, 2))
    start_credit_nt = fields.Float(string="Có đầu kỳ (NT)", digits=(16, 2))
    ps_debit_nt = fields.Float(string="PS nợ (NT)", digits=(16, 2))
    ps_credit_nt = fields.Float(string="PS có (NT)", digits=(16, 2))
    end_debit_nt = fields.Float(string="Nợ cuối kỳ (NT)", digits=(16, 2))
    end_credit_nt = fields.Float(string="Có cuối kỳ (NT)", digits=(16, 2))

    currency_id = fields.Many2one('res.currency', string="Tiền tệ", default=lambda s: s.env.company.currency_id)
    note = fields.Char(string="Ghi chú")

    def unlink(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.state != 'draft':
                raise UserError(_("Không thể xóa dòng khi phiếu đã gửi duyệt!"))
        return super().unlink()
