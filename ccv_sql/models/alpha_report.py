# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date, time
from odoo.exceptions import Warning, ValidationError
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)

class AlphaReport(models.TransientModel):
    _name = 'alpha.report'
    _description = 'Alpha Report'

    name = fields.Char(default="")
    user_id = fields.Many2one('res.users', string="Người phụ trách", readonly=1)
    date = fields.Date(string="Date create", default=date.today())
    line_ids = fields.One2many('alpha.report.line', 'parent_id', string="Tổng hợp công nợ nhân viên")
    line2_ids = fields.One2many('alpha.report.line2', 'parent_id', string="Chi tiết công nợ phải trả")
    line2_tax_ids = fields.One2many(
        'alpha.report.line2',
        'parent_id',
        string="Chi tiết công nợ phải trả (không bao gồm tax)",
        compute='_compute_line2_ids',
        store=False
    )
    line3_ids = fields.One2many('alpha.report.line3', 'parent_id', string="Chi tiết công nợ phải thu")
    line3_tax_ids = fields.One2many(
        'alpha.report.line3',
        'parent_id',
        string="Chi tiết công nợ phải thu (không bao gồm tax)",
        compute='_compute_line3_ids',
        store=False
    )
    line4_ids = fields.One2many('alpha.report.line4', 'parent_id', string="Sổ kế toán chi tiết quỹ tiền mặt")
    line5_ids = fields.One2many('alpha.report.line5', 'parent_id', string="Giấy Thanh Toán Tiền Tạm Ứng")
    line6_ids = fields.One2many('alpha.report.line6', 'parent_id', string="Báo cáo số dư ngân hàng")
    line7_ids = fields.One2many('alpha.report.line7', 'parent_id', string="Danh sách chi tiết vốn tự có")
    date_from = fields.Date(string="Từ ngày", default=date.today().strftime('%Y-%m-01'))
    date_to = fields.Date(string="Đến ngày", default=date.today())
    page_break = fields.Boolean(string="Xuống dòng khi in", default=False)

    type = fields.Selection(
        [("bao_cao_so_du_ngan_hang", "Báo cáo số dư ngân hàng"), ("chi_tiet_cong_no_phai_thu", "Chi Tiết Công Nợ Phải Thu"),
         ("chi_tiet_cong_no_phai_tra", "Chi Tiết Công Nợ Phải Trả"), ('danh_sach_chi_tiet_von_tu_co', ''),
         ('giay_thanh_toan_tien_tam_ung', ''), ('so_chi_tiet_ke_toan_quy_tien_mat', 'Sổ Kế Toán Chi Tiết Quỹ Tiền Mặt'),
         ('tong_hop_cong_no_nhan_vien', 'Tổng Hợp Công Nợ Nhân Viên')], default="danh_sach_chi_tiet_von_tu_co",
        string="Loại báo cáo")
    account_ids = fields.Many2many("account.account", string="Tài khoản")
    account_id = fields.Many2one("account.account", string="Tài khoản")
    partner_ids = fields.Many2many("res.partner", string="Khách hàng / Nhà cung cấp")
    partner_id = fields.Many2one("res.partner", string="Khách hàng")
    partner_type = fields.Selection([('in', 'Trong nước'), ('out', 'Ngoài nước')], default='in', string="Loại nhà cung cấp")
    employee_id = fields.Many2one("hr.employee", string="Nhân viên")
    department_id = fields.Many2one("hr.department", string="Phòng ban", related="employee_id.department_id")
    department = fields.Char(string="Bộ phận")
    is_wizard = fields.Boolean()

    voter_id = fields.Many2one("res.users", string="Người lập phiếu")
    unit_heads_id = fields.Many2one("res.users", string="Thủ trưởng đơn vị")
    chief_acc_id =  fields.Many2one('res.users', string="Kế toán trưởng")
    chief_dept_id =  fields.Many2one('res.users', string="Trưởng bộ phận")
    debt_accountant_id = fields.Many2one('res.users', string="Kế toán tổng hợp")
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('approve', 'Đang duyệt'),
        ('approved', 'Đã phê duyệt'),
    ], string="Trạng thái", default='draft')

    report_type = fields.Selection(string="Loại báo cáo", selection=[
        ('1', 'Một khách hàng'),
        ('is_many_partner', 'Nhiều khách hàng (tự chọn)'),
        ('team', 'Theo khu vực'),
        ('is_all_partner', 'Tất cả khách hàng'),
    ], default='1')
    partner_state = fields.Selection(string="Trạng thái trường khách hàng", selection=[
        ('0', 'Ẩn'),
        ('1', 'Một'),
        ('2', 'Nhiều'),
    ], compute="_compute_partner_state")

    team_id = fields.Many2many("crm.team", string='Đội bán hàng')
    
    @api.depends('line2_ids')
    def _compute_line2_ids(self):
        for rec in self:
            rec.line2_tax_ids = rec.line2_ids.filtered(lambda l: l.display_type != 'tax')
            
    @api.depends('line3_ids')
    def _compute_line3_ids(self):
        for rec in self:
            rec.line3_tax_ids = rec.line3_ids.filtered(lambda l: l.display_type != 'tax')

    @api.depends('type','report_type')
    def _compute_partner_state(self):
        if self.type == 'giay_thanh_toan_tien_tam_ung':
            self.partner_state = '1'
        elif self.type in ('chi_tiet_cong_no_phai_thu','chi_tiet_cong_no_phai_tra'):
            if self.report_type == 'is_many_partner':
                self.partner_state = '2'
            elif self.report_type in ('team', 'is_all_partner'):
                self.partner_state = '0'
            else:
                self.partner_state = '1'
        else:
            self.partner_state = '0'

    def convert_today(self):
        today = date.today()
        return "Ngày %s tháng %s năm %s" % (today.day, today.month, today.year)

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


    @api.model
    def create(self, vals):
        if 'type' in vals and not vals.get('name'):
            if vals['type'] == 'bao_cao_so_du_ngan_hang':
                vals['name'] = "Báo cáo số dư ngân hàng"
            elif vals['type'] == 'chi_tiet_cong_no_phai_thu':
                vals['name'] = "Chi Tiết Công Nợ Phải Thu"
            elif vals['type'] == 'chi_tiet_cong_no_phai_tra':
                vals['name'] = "Chi Tiết Công Nợ Phải Trả"
            elif vals['type'] == 'danh_sach_chi_tiet_von_tu_co':
                vals['name'] = "Danh Sách Chi Tiết Vốn Tự Có"
            elif vals['type'] == 'giay_thanh_toan_tien_tam_ung':
                vals['name'] = "Giấy Thanh Toán Tiền Tạm Ứng"
            elif vals['type'] == 'so_chi_tiet_ke_toan_quy_tien_mat':
                vals['name'] = "Sổ Kế Toán Chi Tiết Quỹ Tiền Mặt"
            elif vals['type'] == 'tong_hop_cong_no_nhan_vien':
                vals['name'] = "Tổng Hợp Công Nợ Nhân Viên"
        return super(AlphaReport, self).create(vals)

    def action_open_alpha_report(self):
        chief_dept_id = int(self.env['ir.config_parameter'].sudo().get_param('ccv_sql.chief_business_department_id', self.env.user.id))
        return {
            'name': 'Báo cáo',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'alpha.report',
            'view_id': self.env.ref('ccv_sql.form_alpha_report_view').id,
            'context': {
                "default_type": "",
                "default_voter_id": self.env.user.id,
                "default_unit_heads_id": int(self.env['ir.config_parameter'].sudo().get_param('ccv_sql.unit_head_id', self.env.user.id)),
                "default_chief_acc_id": int(self.env['ir.config_parameter'].sudo().get_param('ccv_sql.chief_accountant_id', self.env.user.id)),
                "default_chief_dept_id": chief_dept_id,
            }
        }

    def action_open_alpha_sale_report(self):
        res = self.action_open_alpha_report()
        res['context']['default_type'] = "chi_tiet_cong_no_phai_thu"
        res['context']['default_is_sale'] = True
        return res

    @api.onchange("partner_type")
    def onchange_partner_type(self):
        if self.type == 'chi_tiet_cong_no_phai_tra':
            account_id = self.env['account.account'].search([('code', '=', '3311')], limit=1)
            if len(account_id) > 0:
                self.account_id = account_id.id
            self.report_type = '1'
        elif self.type == 'chi_tiet_cong_no_phai_thu':
            account_id = self.env['account.account'].search([('code', '=', '1311')], limit=1)
            if len(account_id) > 0:
                self.account_id = account_id.id
            self.report_type = '1'

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        if self.type == 'giay_thanh_toan_tien_tam_ung':
            self.department = self.partner_id.contact_address_complete
            employee_ids = self.env['hr.employee'].search([('user_id.partner_id', '=', self.partner_id.id)], )
            if len(employee_ids) > 0:
                if employee_ids[0].department_id:
                    self.department = employee_ids[0].department_id.name

    @api.onchange("type")
    def onchange_type(self):
        self.account_ids = False
        self.account_id = False
        self.line_ids = False
        self.line2_ids = False
        self.line3_ids = False
        self.line4_ids = False
        self.line5_ids = False
        self.line6_ids = False
        self.line7_ids = False
        self.partner_id = False
        if self.type == 'bao_cao_so_du_ngan_hang':
            self.name = "Báo cáo số dư ngân hàng"
            account_ids = self.env['account.account'].search([('code', 'like', '112%')])
            account_ids = account_ids.filtered(lambda x: x.code[0:3] == '112')
            if len(account_ids) > 0:
                self.account_ids = account_ids.ids
        if self.type == 'chi_tiet_cong_no_phai_thu':
            self.name = "Chi Tiết Công Nợ Phải Thu"
            self.report_type = '1'
            account_id = self.env['account.account'].search([('code', '=', '13111')], limit=1)
            if len(account_id) > 0:
                self.account_id = account_id.id
        if self.type == 'chi_tiet_cong_no_phai_tra':
            self.name = "Chi Tiết Công Nợ Phải Trả"
            self.report_type = '1'
            if self.partner_type == 'in':
                account_id = self.env['account.account'].search([('code', '=', '3311')], limit=1)
                if len(account_id) > 0:
                    self.account_id = account_id.id
            else:
                account_id = self.env['account.account'].search([('code', '=', '3312')], limit=1)
                if len(account_id) > 0:
                    self.account_id = account_id.id
        if self.type == 'danh_sach_chi_tiet_von_tu_co':
            self.name = "Danh Sách Chi Tiết Vốn Tự Có"
        if self.type == 'giay_thanh_toan_tien_tam_ung':
            self.name = "Giấy Thanh Toán Tiền Tạm Ứng"
            account_id = self.env['account.account'].search([('code', '=', '1411')], limit=1)
            if len(account_id) > 0:
                self.account_id = account_id.id
        if self.type == 'so_chi_tiet_ke_toan_quy_tien_mat':
            self.name = "Sổ Kế Toán Chi Tiết Quỹ Tiền Mặt"
            account_id = self.env['account.account'].search([('code', '=', '11111')], limit=1)
            if len(account_id) > 0:
                self.account_id = account_id.id
        if self.type == 'tong_hop_cong_no_nhan_vien':
            account_ids = self.env['account.account'].search([('code', '=', '1411')])
            self.name = "Tổng Hợp Công Nợ Nhân Viên"
            if len(account_ids) > 0:
                self.account_ids = account_ids.ids
                self.account_id = account_ids[0].id
        if self.type == 'danh_sach_chi_tiet_von_tu_co':
            self.name = "Danh sách chi tiết vốn tự có"
            account_ids = self.env['account.account'].search([('code', '=', '621')], limit=1)
            if len(account_ids) > 0:
                self.account_ids = account_ids.ids
                self.account_id = account_ids[0].id

    def action_print_report_tax(self):
        if self.type == 'chi_tiet_cong_no_phai_thu':
            return self.env.ref('ccv_sql.chi_tiet_cong_no_phai_thu_tax_report').report_action(self)

    
    def action_confirm(self):
        self.line_ids = False
        self.line2_ids = False
        self.line3_ids = False
        self.line4_ids = False
        self.line5_ids = False
        self.line6_ids = False
        self.line7_ids = False
        if self.type == 'bao_cao_so_du_ngan_hang':
            self.sudo().report_bao_cao_so_du_ngan_hang()
        if self.type == 'chi_tiet_cong_no_phai_thu':
            self.sudo().report_chi_tiet_cong_no_phai_thu()
        if self.type == 'chi_tiet_cong_no_phai_tra':
            self.sudo().report_chi_tiet_cong_no_phai_tra()
        if self.type == 'danh_sach_chi_tiet_von_tu_co':
            self.sudo().report_danh_sach_chi_tiet_von_tu_co()
        if self.type == 'giay_thanh_toan_tien_tam_ung':
            self.sudo().report_giay_thanh_toan_tien_tam_ung()
        if self.type == 'so_chi_tiet_ke_toan_quy_tien_mat':
            self.sudo().report_so_chi_tiet_ke_toan_quy_tien_mat()
        if self.type == 'tong_hop_cong_no_nhan_vien':
            if self.account_id:
                self.account_ids = self.account_id.ids
            self.sudo().report_tong_hop_cong_no_nhan_vien()

    def report_bao_cao_so_du_ngan_hang(self):
        par_names = 'date_to,account_ids,id'
        par_names = self.access_begin(par_names)
        sp_name = 'select * from function_bao_cao_so_du_ngan_hang(%s, %s, %s)'
        self.env.cr.execute(sp_name, (par_names))
        # for line in self.line6_ids:
        #     if line.account_id.currency_id and line.account_id.currency_id.id != 23:
        #         line.total = line.end_debit * line.account_id.currency_id.rate_ids[0].inverse_company_rate
        #     else:
        #         line.total = line.end_debit
    
    def _get_partner(self):
        partner_ids = self.env['res.partner']
        if self.type in ('chi_tiet_cong_no_phai_thu', 'chi_tiet_cong_no_phai_tra'):
            if self.report_type == 'is_many_partner':
                partner_ids = self.partner_ids
            elif self.report_type == 'is_all_partner':
                partner_ids = self._get_debt_report_partners()
            elif self.report_type == 'team':
                partner_ids = self._get_debt_report_partners(team_ids=self.team_id)
            else:
                partner_ids = self.partner_id
        return partner_ids

    def _get_debt_report_partners(self, team_ids=False):
        partner_env = self.env['res.partner'].sudo()
        if not self.account_id:
            return partner_env
        params = [self.account_id.id]
        sql = """
            SELECT aml.partner_id
            FROM account_move_line aml
            JOIN res_partner rp ON rp.id = aml.partner_id
            WHERE aml.parent_state = 'posted'
              AND aml.account_id = %s
              AND aml.partner_id IS NOT NULL
        """
        if team_ids is not False:
            if not team_ids:
                return partner_env
            placeholders = ','.join(['%s'] * len(team_ids))
            sql += f" AND rp.team_id IN ({placeholders})"
            params.extend(team_ids.ids)
        params.extend([self.date_from, self.date_from, self.date_to])
        sql += """
            GROUP BY aml.partner_id
            HAVING
                SUM(CASE WHEN aml.date < %s THEN aml.debit - aml.credit ELSE 0 END) <> 0
                OR SUM(CASE WHEN aml.date >= %s AND aml.date <= %s THEN aml.debit + aml.credit ELSE 0 END) <> 0
            ORDER BY aml.partner_id
        """
        self.env.cr.execute(sql, tuple(params))
        return partner_env.browse([row[0] for row in self.env.cr.fetchall()])

    def report_chi_tiet_cong_no_phai_thu(self):
        if self.report_type in ("is_many_partner", "team", "is_all_partner"):
            if self.line3_ids:
                self.line3_ids.unlink()
            partner_ids = self._get_partner()
            sp_name = ["select * from function_chi_tiet_cong_no_phai_thu('%s', '%s', %s, %s, %s, false)" % (self.date_from,self.date_to,self.account_id.id,partner_id.id,self.id)
                    for partner_id in partner_ids]
            self.env.cr.execute('; '.join(sp_name))
            self.sudo().env.cr.commit()
        else:
            par_names = 'date_from,date_to,account_id,partner_id,id'
            par_names = self.access_begin(par_names)
            sp_name = 'select * from function_chi_tiet_cong_no_phai_thu(%s, %s, %s, %s, %s, true)'
            self.env.cr.execute(sp_name, (par_names))
        if len(self.line3_ids) > 0:
            self.action_compute_end()
            self._remove_empty_start_balance_lines('line3_ids')

    def _remove_empty_start_balance_lines(self, line_name):
        line_ids = getattr(self, line_name)
        empty_start_lines = line_ids.filtered(
            lambda line:
                not line.date
                and not line.move_id
                and not line.debit
                and not line.credit
                and not line.end_debit
                and not line.end_credit
        )
        if empty_start_lines:
            empty_start_lines.unlink()

    def report_chi_tiet_cong_no_phai_tra(self):
        if self.report_type in ("is_many_partner", "team", "is_all_partner"):
            if self.line2_ids:
                self.line2_ids.unlink()
            partner_ids = self._get_partner()
            sp_name = ["select * from function_chi_tiet_cong_no_phai_tra('%s', '%s', %s, %s, %s, false)" % (self.date_from,self.date_to,self.account_id.id,partner_id.id,self.id)
                    for partner_id in partner_ids]
            self.env.cr.execute(';'.join(sp_name))
            self.sudo().env.cr.commit()
        else:
            par_names = 'date_from,date_to,account_id,partner_id,id'
            par_names = self.access_begin(par_names)
            sp_name = 'select * from function_chi_tiet_cong_no_phai_tra(%s, %s, %s, %s, %s, true)'
            self.env.cr.execute(sp_name, (par_names))
        if len(self.line2_ids) > 0:
            self.action_compute_end()

    def action_compute_end(self):
        line_ids = False
        line_tax_ids = False
        start = 0
        if len(self.line2_ids) > 0 or len(self.line3_ids) > 0:
            line_name = 'line2_ids'
            line_tax_name = 'line2_tax_ids'
            if len(self.line3_ids) > 0:
                line_name = 'line3_ids'
                line_tax_name = 'line3_tax_ids'
            getattr(self,'_compute_' + line_name)()
            if self.report_type in ("is_many_partner", "team", "is_all_partner"):
                partner_ids = self._get_partner()
                for partner_id in partner_ids:
                    line_ids, start = self._get_data_compute_w_groupby(line_name, partner_id.id, 'partner_id')
                    if line_ids:
                        self._compute_line_debit_credit(line_ids, start)
                    line_ids, start = self._get_data_compute_w_groupby(line_tax_name, partner_id.id, 'partner_id')
                    if line_ids:
                        self._compute_line_debit_credit_w_tax(line_ids, start)
                return
            else:
                line_ids = getattr(self,line_name)
                start = line_ids[0].end_debit if line_ids[0].end_debit > 0 else - line_ids[0].end_credit
                line_ids = line_ids[1:]
                
                line_tax_ids = getattr(self,line_tax_name)
                line_tax_ids[0].end_debit
                start = line_tax_ids[0].end_debit if line_tax_ids[0].end_debit > 0 else - line_tax_ids[0].end_credit
                line_tax_ids[0].end_w_tax_debit = line_tax_ids[0].end_debit
                line_tax_ids[0].end_w_tax_credit = line_tax_ids[0].end_credit
                line_tax_ids = line_tax_ids[1:]
        elif len(self.line4_ids) > 0:
            line_ids = self.line4_ids
            start = line_ids[0].end_debit if line_ids[0].end_debit > 0 else - line_ids[0].end_credit
            line_ids = line_ids[1:]
        if line_ids:
            self._compute_line_debit_credit(line_ids, start)
        if line_tax_ids:
            self._compute_line_debit_credit_w_tax(line_tax_ids, start)

    def _get_data_compute_w_groupby(self, line_name, field_id, field_name):
        line_ids = getattr(self,line_name).filtered(lambda l: getattr(l,field_name).id == field_id)
        if not line_ids:
            return False, False
        start = line_ids[0].end_debit if line_ids[0].end_debit > 0 else - line_ids[0].end_credit
        lines = line_ids[1:]
        return lines, start
    
    def _compute_line_debit_credit(self, line_ids, start_line):
        start = start_line
        for line in line_ids:
            end_debit = 0
            end_credit = 0
            if line.debit > 0:
                if start >= 0:
                    end_debit = start + line.debit
                    start = start + line.debit
                elif start <= 0 and start + line.debit <= 0:
                    end_credit = start + line.debit
                    start = start + line.debit
                elif start <= 0 and start + line.debit >= 0:
                    end_debit = start + line.debit
                    start = start + line.debit
            else:
                if start <= 0:
                    end_credit = start - line.credit
                    start = start - line.credit
                elif start >= 0 and start - line.credit >= 0:
                    end_debit = start - line.credit
                    start = start - line.credit
                elif start >= 0 and start - line.credit <= 0:
                    end_credit = start - line.credit
                    start = start - line.credit
            line.write({
                'end_debit': end_debit if end_debit > 0 else 0,
                'end_credit': - end_credit if end_credit < 0 else 0,
                'partner_type': 'in' if self.partner_type == 'in' else 'out',
            })
    
    def _compute_line_debit_credit_w_tax(self, line_ids, start_line):
        start = start_line
        for line in line_ids:
            end_debit = 0
            end_credit = 0
            if line.debit > 0:
                debit = start + (line.debit + line.amount_tax)
                if start >= 0:
                    end_debit = debit
                    start = debit
                elif start <= 0 and debit <= 0:
                    end_credit = debit
                    start = debit
                elif start <= 0 and debit >= 0:
                    end_debit = debit
                    start = debit
            else:
                credit = start - (line.credit + line.amount_tax)
                if start <= 0:
                    end_credit = credit
                    start = credit
                elif start >= 0 and credit >= 0:
                    end_debit = credit
                    start = credit
                elif start >= 0 and credit <= 0:
                    end_credit = credit
                    start = credit
            line.write({
                'end_w_tax_debit': end_debit if end_debit > 0 else 0,
                'end_w_tax_credit': - end_credit if end_credit < 0 else 0,
                'partner_type': 'in' if self.partner_type == 'in' else 'out',
            })

    def report_danh_sach_chi_tiet_von_tu_co(self):
        par_names = 'date_to,account_ids,id'
        par_names = self.access_begin(par_names)
        sp_name = 'select * from function_danh_sach_chi_tiet_von_tu_co(%s, %s, %s)'
        self.env.cr.execute(sp_name, (par_names))

    def report_giay_thanh_toan_tien_tam_ung(self):
        par_names = 'date_from,date_to,account_id,partner_id,id'
        par_names = self.access_begin(par_names)
        sp_name = 'select * from function_giay_thanh_toan_tien_tam_ung(%s, %s, %s, %s, %s)'
        self.env.cr.execute(sp_name, (par_names))

    def report_so_chi_tiet_ke_toan_quy_tien_mat(self):
        par_names = 'date_from,date_to,account_id,id'
        par_names = self.access_begin(par_names)
        sp_name = 'select * from function_so_chi_tiet_ke_toan_quy_tien_mat(%s, %s, %s, %s)'
        self.env.cr.execute(sp_name, (par_names))
        self.action_compute_end()

    def report_tong_hop_cong_no_nhan_vien(self):
        par_names = 'date_from,date_to,account_ids,id'
        par_names = self.access_begin(par_names)
        sp_name = 'select * from function_tong_hop_cong_no_nhan_vien(%s, %s, %s, %s)'
        self.env.cr.execute(sp_name, (par_names))

    def access_begin(self, par_names):
        par_values = []
        for par in par_names.split(','):
            try:
                if self._fields[par].type == "many2one":
                    a = self.mapped(par)[0].id
                    par_values.append(a)
                elif self._fields[par].type == "many2many":
                    string = ''
                    if self.mapped(par):
                        for line in self.mapped(par):
                            string = string + str(line.id) + ','
                        string = string[:-1]
                    par_values.append(string)
                elif self._fields[par].type == "selection":
                    string = self.mapped(par)[0]
                    if string:
                        par_values.append(string)
                    else:
                        par_values.append('')
                else:
                    par_values.append(self.mapped(par)[0])
            except:
                par_values.append(None)
        return par_values

    def action_view_tree(self):
        vals = {
            'name': "Tree view",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'alpha.report.line',
            'domain': [('id', 'in', self.line_ids.ids)],
            'context': {
                'create': False,
                'edit': False
            }
        }
        if self.type == "tong_hop_cong_no_nhan_vien":
            vals.update({
                'view_id': self.env.ref('ccv_sql.tree_tong_hop_cong_no_nhan_vien').id,
                'name': "Tổng Hợp Công Nợ Nhân Viên",
            })
        elif self.type == "chi_tiet_cong_no_phai_tra":
            if self.partner_type == 'out':
                vals.update({
                    'view_id': self.env.ref('ccv_sql.tree_chi_tiet_cong_no_phai_tra').id,
                    'name': "Chi tiết công nợ phải trả",
                    'res_model': 'alpha.report.line2',
                    'domain': [('id', 'in', self.line2_ids.ids)],
                })
            else:
                vals.update({
                    'view_id': self.env.ref('ccv_sql.tree_chi_tiet_cong_no_phai_tra_trong_nuoc').id,
                    'name': "Chi tiết công nợ phải trả",
                    'res_model': 'alpha.report.line2',
                    'domain': [('id', 'in', self.line2_ids.ids)],
                })
        elif self.type == "chi_tiet_cong_no_phai_thu":
            vals.update({
                'view_id': self.env.ref('ccv_sql.tree_chi_tiet_cong_no_phai_thu').id,
                'name': "Chi tiết công nợ phải thu",
                'res_model': 'alpha.report.line3',
                'domain': [('id', 'in', self.line3_ids.ids)],
            })
        elif self.type == "so_chi_tiet_ke_toan_quy_tien_mat":
            vals.update({
                'view_id': self.env.ref('ccv_sql.tree_so_chi_tiet_ke_toan_quy_tien_mat').id,
                'name': "Sổ kế toán chi tiết quỹ tiền mặt",
                'res_model': 'alpha.report.line4',
                'domain': [('id', 'in', self.line4_ids.ids)],
            })
        elif self.type == "giay_thanh_toan_tien_tam_ung":
            vals.update({
                'view_id': self.env.ref('ccv_sql.tree_giay_thanh_toan_tien_tam_ung').id,
                'name': "Giấy thanh toán tiền tạm ứng",
                'res_model': 'alpha.report.line5',
                'domain': [('id', 'in', self.line5_ids.ids)],
            })
        elif self.type == "bao_cao_so_du_ngan_hang":
            vals.update({
                'view_id': self.env.ref('ccv_sql.tree_bao_cao_so_du_ngan_hang').id,
                'name': "Báo cáo số dư ngân hàng",
                'res_model': 'alpha.report.line6',
                'domain': [('id', 'in', self.line6_ids.ids)],
            })
        elif self.type == "danh_sach_chi_tiet_von_tu_co":
            vals.update({
                'view_id': self.env.ref('ccv_sql.tree_danh_sach_chi_tiet_von_tu_co').id,
                'name': "Danh sách chi tiết vốn tự có",
                'res_model': 'alpha.report.line7',
                'domain': [('id', 'in', self.line7_ids.ids)],
            })
        return vals

    def action_print_pdf_report(self):
        if self.type == 'tong_hop_cong_no_nhan_vien':
            return self.env.ref('ccv_sql.tong_hop_cong_no_nhan_vien_report').report_action(self)
        elif self.type == 'so_chi_tiet_ke_toan_quy_tien_mat':
            return self.env.ref('ccv_sql.so_chi_tiet_ke_toan_quy_tien_mat_report').report_action(self)
        elif self.type == "chi_tiet_cong_no_phai_tra":
            if self.partner_type == 'out':
                return self.env.ref('ccv_sql.chi_tiet_cong_no_phai_tra_report').report_action(self)
            else:
                return self.env.ref('ccv_sql.chi_tiet_cong_no_phai_tra_trong_nuoc_report').report_action(self)
        elif self.type == "chi_tiet_cong_no_phai_thu":
            return self.env.ref('ccv_sql.chi_tiet_cong_no_phai_thu_report').report_action(self)
        elif self.type == "giay_thanh_toan_tien_tam_ung":
            return self.env.ref('ccv_sql.giay_thanh_toan_tien_tam_ung_report').report_action(self)
        elif self.type == "bao_cao_so_du_ngan_hang":
            return self.env.ref('ccv_sql.bao_cao_so_du_ngan_hang_report').report_action(self)
        elif self.type == "danh_sach_chi_tiet_von_tu_co":
            return self.env.ref('ccv_sql.danh_sach_chi_tiet_von_tu_co_report').report_action(self)

    def action_print_xlsx_report(self):
        pass

    def action_print_excel(self):
        if self.type == 'account':
            self.write({
                'total_start_debit': sum(self.line_ids.mapped("start_debit")),
                'total_start_credit': sum(self.line_ids.mapped("start_credit")),
                'total_debit': sum(self.line_ids.mapped("debit")),
                'total_credit': sum(self.line_ids.mapped("credit")),
                'total_end_debit': sum(self.line_ids.mapped("end_debit")),
                'total_end_credit': sum(self.line_ids.mapped("end_credit"))
            })
            return self.env.ref('ccv_sql.account_move_py3o_action').report_action(self)

    def convert_hour_today(self):
        now = datetime.now()
        return "%s Giờ %s Ngày %s tháng %s năm %s" % (now.hour, now.minute, now.day, now.month, now.year)

    def action_export_stock_quant(self):
        par_names = 'id'
        par_names = self.access_begin(par_names)
        sp_name = 'select * from function_bien_ban_kiem_ke_vat_tu_hang_hoa(%s)'
        self.env.cr.execute(sp_name, (par_names))
        return self.env.ref('ccv_sql.bien_ban_kiem_ke_vat_tu_hang_hoa_report').report_action(self)
