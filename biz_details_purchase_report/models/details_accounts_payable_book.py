# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.fields import Command
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)


class DetailsAccountsPayableBook(models.Model):
    _name = 'details.accounts.payable.book'
    _description = 'Báo cáo chi tiết công nợ phải trả'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _order = 'id desc'

    name = fields.Char(string='Tên')
    date_from = fields.Date(string='Từ ngày', required=True)
    date_to = fields.Date(string='Đến ngày', required=True)
    account_id = fields.Many2one('account.account', string='Tài khoản', required=True)
    partner_type = fields.Selection([
        ('in', 'Trong nước'),
        ('out', 'Ngoài nước'),
    ], string='Loại nhà cung cấp', default='in')
    
    report_type = fields.Selection(string="Loại báo cáo", selection=[
        ('1', 'Một khách hàng'),
        ('is_many_partner', 'Nhiều khách hàng (tự chọn)'),
        ('team', 'Theo khu vực'),
        ('is_all_partner', 'Tất cả khách hàng'),
    ], required=True, default='1')

    partner_state = fields.Selection(string="Trạng thái trường khách hàng", selection=[
        ('1', '1'), 
        ('2', '2'), 
        ('0', '0')
    ], compute='_compute_partner_state')

    partner_id = fields.Many2one("res.partner", string="Khách hàng")
    partner_ids = fields.Many2many("res.partner", string="Khách hàng / Nhà cung cấp")
    team_id = fields.Many2many("crm.team", string="Nhiều khu vực")

    voter_id = fields.Many2one('res.users', string="Người lập phiếu")
    department_head_id = fields.Many2one('res.users', string="Trưởng phòng thương mại")
    chief_accountant_id = fields.Many2one('res.users', string="Kế toán trưởng")
    director_id = fields.Many2one('res.users', string="Thủ trưởng đơn vị")
    check_have_mount = fields.Boolean(string="Có số dư", default=False)
    active = fields.Boolean(default=True)

    line_ids = fields.One2many('details.accounts.payable.book.line', 'parent_id', string="Chi tiết", readonly=True)

    state = fields.Selection(
        [('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'), ('refuse', 'Từ chối'), ('cancel', 'Hủy')],
        'Trạng thái', default='draft', tracking=True)

    trp_approve_history_ids = fields.One2many('trp.approve.history', 'details_accounts_payable_book_id', string='Lịch sử duyệt', copy=False)

    def unlink(self):
        for record in self:
            if record.state not in ['refuse', 'cancel', 'draft']:
                raise UserError("Không thể xóa yêu cầu ký đã duyệt!")
        return super(DetailsAccountsPayableBook, self).unlink()

    def action_cancel(self):
        self.write({'state': 'cancel'})
        res_history = self.trp_approve_history_ids
        self.env['mail.activity'].search([('trp_approve_history_id', 'in', res_history.ids)]).with_context(skip_approve_done=True).action_done()

    def action_undo(self):
        self.write({'state': 'draft'})

    @api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.manager_type',
                 'trp_approve_config_line_id.user_ids', 'trp_approve_config_line_id.job_ids',
                 'department_head_id', 'chief_accountant_id', 'voter_id')
    def _compute_current_approve_users(self):
        super(DetailsAccountsPayableBook, self)._compute_current_approve_users()
        for record in self:
            cfg = record.trp_approve_config_line_id
            if cfg:
                approver_ids = record.current_approve_user_ids.ids
                if cfg.manager_type == 'creator':
                    if record.voter_id:
                        approver_ids.append(record.voter_id.id)
                record.current_approve_user_ids = [(6, 0, list(set(approver_ids)))]

    def action_sign(self):
        self = self.sudo()
        if not self.line_ids:
            raise ValidationError("Vui lòng lấy dữ liệu trước khi trình duyệt!")
        res_approve = {}
        if not self.trp_approve_config_line_id and self.state in ('draft'):
            self.approve_next_action = 'action_sign'
            self.approve_state_init = self.state
            self.approve_state_next = 'approve'
            res_approve = self.with_context(approve_type='new').create_approve()
        if not res_approve or not self.trp_approve_config_line_id:
            if self.state == 'approve':
                self.update({'state': 'approved'})
                return

    def action_agree(self):
        res = super(DetailsAccountsPayableBook, self).action_agree()
        for record in self:
            if record.state == 'approved':
                record.message_post(
                    body=f"Báo cáo chi tiết công nợ phải trả {record._get_html_link()} đã được duyệt.",
                )
        return res

    def convert_print(self, value):
        if not value:
            return ''
        if str(value).find('202') > -1:
            return str(value).split('-')[2] + '/' + str(value).split('-')[1] + '/' + str(value).split('-')[0]
        return value

    def convert_vnd(self, amount):
        a = format(amount, ',.0f')
        return a

    def convert_usd(self, amount):
        a = format(amount, ',.2f')
        return a

    def convert_number(self, amount):
        number = str(round(amount, 3))
        if number.find('.') > -1:
            number = number.split('.')
            head = number[0]
            tail = number[1]
            if len(tail) == 1:
                number = head + '.' + tail + '00'
            elif len(tail) == 2:
                number = head + '.' + tail + '0'
            else:
                number = head + '.' + tail
        else:
            number = number + '.000'
        return number

    def action_print_pdf(self):
        if self.partner_type == 'in':
            return self.env.ref('biz_details_purchase_report.details_accounts_payable_book_trong_nuoc_report').report_action(self)
        else:
            return self.env.ref('biz_details_purchase_report.details_accounts_payable_book_report').report_action(self)

    def action_print_excel(self):
        return self.env.ref('biz_details_purchase_report.action_details_accounts_payable_book_xlsx').report_action(self)

    @api.depends('report_type')
    def _compute_partner_state(self):
        for rec in self:
            if rec.report_type == '1':
                rec.partner_state = '1'
            elif rec.report_type == 'is_many_partner':
                rec.partner_state = '2'
            else:
                rec.partner_state = '0'

    def _get_or_create_alpha_report(self):
        """Tạo bản ghi alpha.report tạm để tái sử dụng logic in ấn hiện có."""
        AlphaReport = self.env['alpha.report'].sudo()
        
        vals = {
            'type': 'chi_tiet_cong_no_phai_tra',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'account_id': self.account_id.id,
            'partner_type': self.partner_type,
            'report_type': self.report_type,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'partner_ids': [(6, 0, self.partner_ids.ids)] if self.partner_ids else False,
            'team_id': [(6, 0, self.team_id.ids)] if self.team_id else False,
        }

        return AlphaReport.create(vals)

    @api.model
    def default_get(self, fields_list):
        defaults = super(DetailsAccountsPayableBook, self).default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()

        department_head_id = env_params.get_param('biz_details_purchase_report.payable_department_head_id', False)
        chief_accountant_id = env_params.get_param('biz_details_purchase_report.payable_chief_accountant_id', False)
        director_id = env_params.get_param('biz_details_purchase_report.payable_director_id', False)

        # Retrieve default account 3311
        account_3311 = self.env['account.account'].sudo().search([('code', '=', '3311'), ('company_id', '=', self.env.company.id)], limit=1)

        defaults.update({
            'name': f'Chi tiết công nợ phải trả ngày {date.today().strftime("%d-%m-%Y")}',
            'voter_id': self.env.user.id,
            'date_from': date.today().replace(day=1),
            'date_to': date.today(),
            'department_head_id': int(department_head_id) if (department_head_id and department_head_id != '0') else False,
            'chief_accountant_id': int(chief_accountant_id) if (chief_accountant_id and chief_accountant_id != '0') else False,
            'director_id': int(director_id) if (director_id and director_id != '0') else False,
        })
        
        if account_3311:
            defaults['account_id'] = account_3311.id
            
        return defaults

    def action_confirm(self):
        """Lấy dữ liệu - Gọi hàm SQL gốc từ alpha.report rồi copy kết quả sang model này."""
        self.ensure_one()
        self.line_ids.unlink()

        # Tạo alpha.report tạm
        alpha_report = self._get_or_create_alpha_report()

        # Gọi hàm lấy dữ liệu gốc
        alpha_report.action_confirm()

        # Invalidate cache để đọc lại line2_ids từ DB (vì SQL function ghi trực tiếp)
        alpha_report.invalidate_cache(['line2_ids'], [alpha_report.id])

        # Copy dữ liệu sang model line của mình
        data = []
        for line in alpha_report.line2_ids:
            data.append(Command.create({
                'partner_id': line.partner_id.id if line.partner_id else False,
                'partner_code': line.partner_code,
                'partner_type': line.partner_type,
                'invoice_date': line.invoice_date,
                'date': line.date,
                'move_id': line.move_id.id if line.move_id else False,
                'reference': line.reference,
                'note': line.note,
                'account_id': line.account_id.id if line.account_id else False,
                'account_dest_id': line.account_dest_id.id if line.account_dest_id else False,
                'amount_tax': line.amount_tax,
                'debit': line.debit,
                'credit': line.credit,
                'end_debit': line.end_debit,
                'end_credit': line.end_credit,
                'product_uom_qty': line.product_uom_qty,
                'price_unit': line.price_unit,
                'uom_id': line.uom_id.id if line.uom_id else False,
            }))

        if data:
            self.write({'line_ids': data})

        # Nếu bật "Có số dư", lọc bỏ các dòng mà end_debit = 0 và end_credit = 0
        if self.check_have_mount:
            lines_to_remove = self.line_ids.filtered(lambda l: l.end_debit <= 0 and l.end_credit <= 0)
            lines_to_remove.unlink()
