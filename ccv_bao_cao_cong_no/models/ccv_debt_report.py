from odoo import models, fields, api
import logging
import json
import ast
from datetime import datetime, date
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ccv_debt_report(models.Model):
    _name = "ccv.debt.report"
    _order = "date_from"

    name = fields.Char(string="Tên")
    parent_id = fields.Many2one("ccv.debt.report", string="Đầu kỳ")

    state = fields.Selection(
        string="Trạng thái",
        selection=[
            ("new", "Mới"),
            ("locked", "Khóa"),
        ],
        default="new",
        readonly=True,
    )

    type = fields.Selection(
        string="Loại báo cáo",
        selection=[
            ("cong_no_phai_thu", "Công nợ phải thu"),
            ("cong_no_phai_tra", "Công nợ phải trả"),
        ],
    )

    partner_id = fields.Many2one("res.partner", string="Khách hàng/NCC")
    partner_ids = fields.Many2many("res.partner", string="Khách hàng/NCC")
    account_id = fields.Many2one("account.account", string="Tài khoản")
    account_ids = fields.Many2many("account.account", string="Tài khoản")

    domain = fields.Char(string="Domain", store=True, compute="_compute_domain_report")

    line_ids = fields.One2many(
        "ccv.debt.report.line1",
        "parent_id",
        string="Chi tiết Công nợ phải thu",
        store=True,
        readonly=True,
        copy=False,
    )

    line1_ids = fields.Many2many(
        "ccv.debt.report.line1",
        "ccv_debt_report_line1_rel",  # Bảng quan hệ riêng
        "report_id", "line1_id",  # Cột liên kết
        string="Chi tiết Công nợ phải thu",
        store=True,
        readonly=True,
        copy=False,
    )

    line1_nt_ids = fields.Many2many(
        "ccv.debt.report.line1",
        "ccv_debt_report_line1_nt_rel",  # Bảng quan hệ riêng
        "report_id", "line1_id",  # Cột liên kết
        string="Chi tiết Công nợ phải thu Ngoại tệ",
        store=True,
        readonly=True,
        copy=False,
    )

    line1_th_ids = fields.Many2many(
        "ccv.debt.report.line1",
        "ccv_debt_report_line1_th_rel",  # Bảng quan hệ khác
        "report_id", "line1_id",  # Cột liên kết
        string="Tổng hợp Công nợ phải thu",
        store=True,
        readonly=True,
        copy=False,
    )

    line1_th_nt_ids = fields.Many2many(
        "ccv.debt.report.line1",
        "ccv_debt_report_line1_th_nt_rel",  # Bảng quan hệ khác
        "report_id", "line1_id",  # Cột liên kết
        string="Tổng hợp Công nợ phải thu Ngoại tệ",
        store=True,
        readonly=True,
        copy=False,
    )

    line2_ids = fields.Many2many(
        "ccv.debt.report.line1",
        "ccv_debt_report_line1_rel",  # Bảng quan hệ riêng
        "report_id", "line1_id",  # Cột liên kết
        string="Chi tiết Công nợ phải trả",
        store=True,
        readonly=True,
        copy=False,
    )

    line2_nt_ids = fields.Many2many(
        "ccv.debt.report.line1",
        "ccv_debt_report_line1_nt_rel",  # Bảng quan hệ riêng
        "report_id", "line1_id",  # Cột liên kết
        string="Chi tiết Công nợ phải trả Ngoại tệ",
        store=True,
        copy=False,
        readonly=True,
    )

    line2_th_ids = fields.Many2many(
        "ccv.debt.report.line1",
        "ccv_debt_report_line1_th_rel",  # Bảng quan hệ khác
        "report_id", "line1_id",  # Cột liên kết
        string="Tổng hợp Công nợ phải trả",
        store=True,
        copy=False,
        readonly=True,
    )

    line2_th_nt_ids = fields.Many2many(
        "ccv.debt.report.line1",
        "ccv_debt_report_line1_th_nt_rel",  # Bảng quan hệ khác
        "report_id", "line1_id",  # Cột liên kết
        string="Tổng hợp Công nợ phải trả Ngoại tệ",
        store=True,
        copy=False,
        readonly=True,
    )

    # line2_ids = fields.One2many("ccv.debt.report.line2", 'parent_id', string="Công nợ phải trả", store=True,readonly=True)

    aml_ids = fields.Many2many(
        "account.move.line",
        string="Chi tiết bút toán",
        store=True,
        copy=False,
    )
    am_ids = fields.Many2many(
        "account.move",
        string="Bút toán",
        store=True,
        copy=False,
    )

    currency_id = fields.Many2one("res.currency", string="Tiền tệ")
    is_currency = fields.Boolean(compute="_compute_currency_id")
    is_break = fields.Boolean(string="Sang trang mới", default=False)
    is_sale = fields.Boolean(string="Xuất mẫu kinh doanh", default=False)
    team_id = fields.Many2one("crm.team", string="Đội bán hàng")

    date_from = fields.Date(string="Từ ngày", default=date.today().strftime("%Y-%m-01"))
    date_to = fields.Date(string="Đến ngày", default=date.today())

    report_type = fields.Selection(string="Loại báo cáo", selection=[
        ('1', 'Một khách hàng'),
        ('is_many_partner', 'Nhiều khách hàng (tự chọn)'),
        ('team', 'Theo khu vực'),
        ('is_all_partner', 'Tất cả khách hàng'),
    ], default='1')

    voter_id = fields.Many2one("res.users", string="Người lập phiếu")
    lead_team_id = fields.Many2one("res.users", string="Trưởng khu vực")
    lead_sale_id = fields.Many2one("res.users", string="Trưởng phòng kinh doanh")
    chief_acc_id = fields.Many2one("res.users", string="Kế toán trưởng")
    unit_heads_id = fields.Many2one("res.users", string="Thủ trưởng đơn vị")

    @api.model
    def default_get(self, fields_list):
        defaults = super(ccv_debt_report, self).default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()

        defaults.update({
            'unit_heads_id': int(env_params.get_param('ccv_bao_cao_cong_no.unit_heads_id', 0)),
            'chief_acc_id': int(env_params.get_param('ccv_bao_cao_cong_no.chief_acc_id', 0)),
            'lead_sale_id': int(env_params.get_param('ccv_bao_cao_cong_no.lead_sale_id', 0)),
            'voter_id': self.env.user.id,
        })

        if 'team_id' in fields_list:
            defaults['lead_team_id'] = self.team_id.user_id.id if self.team_id and self.team_id.user_id else False

        return defaults

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, '%s - %s - %s' % (rec.name, rec.date_from.strftime("%d/%m/%Y") if rec.date_from else "", rec.date_to.strftime("%d/%m/%Y") if rec.date_to else "")))
        return result

    @api.onchange("report_type")
    def _onchange_report_type(self):
        for rec in self.sudo():
            rec.partner_id = False
            rec.partner_ids = False
            if rec.report_type == 'team':
                team_id = self.env['crm.team'].search([
                    '|', '|',
                    ('user_id','=',self.env.user.id),
                    ('member_ids','in',[self.env.user.id]),
                    ('sales_assistant_ids','in',[self.env.user.id]),
                ], limit=1)
                rec.team_id = team_id
            else:
                rec.team_id = False

    @api.onchange("team_id")
    def _onchange_team_id(self):
        for rec in self.sudo():
            rec.lead_team_id = rec.team_id.user_id.id if rec.team_id and rec.team_id.user_id else False
    
    @api.depends("currency_id")
    def _compute_currency_id(self):
        for rec in self.sudo():
            rec.is_currency = True if rec.currency_id and rec.currency_id.name != "VND" else False

    def _compute_line(self, type='chi-tiet'):
        for rec in self.sudo():
            chi_tiet = rec.line_ids.filtered(lambda l:l.type_line == 'chi_tiet')
            tong_hop = rec.line_ids.filtered(lambda l:l.type_line == 'tong_hop')
            if type == 'chi-tiet':
                if rec.type == 'cong_no_phai_thu':
                    rec.line1_ids = chi_tiet
                    if rec.is_currency:
                        rec.line1_nt_ids = chi_tiet
                elif rec.type == 'cong_no_phai_tra':
                    rec.line2_ids = chi_tiet
                    if rec.is_currency:
                        rec.line2_nt_ids = chi_tiet
            elif type == 'tong-hop':
                if rec.type == 'cong_no_phai_thu':
                    rec.line1_th_ids = tong_hop
                    if rec.is_currency:
                        rec.line1_th_nt_ids = tong_hop
                elif rec.type == 'cong_no_phai_tra':
                    rec.line2_th_ids = tong_hop
                    if rec.is_currency:
                        rec.line2_th_nt_ids = tong_hop

    @api.depends("date_from", "date_to", "partner_ids", "partner_id", "account_ids", "account_ids", "team_id","parent_id","currency_id")
    def _compute_domain_report(self):
        for rec in self.sudo():
            partner_ids = rec.partner_ids + rec.partner_id
            account_ids = rec.account_ids + rec.account_id

            domain = [('parent_state','=','posted')]
            if rec.is_currency and rec.currency_id.id != 2:
                domain += [('currency_id','=',rec.currency_id.id)]
                
            if rec.type == 'cong_no_phai_thu':
                domain += [('move_id.move_type','in',('entry','out_invoice','out_refund'))]
            elif rec.type == 'cong_no_phai_tra':
                domain += [('move_id.move_type','in',('entry','in_invoice','in_refund'))]

            if rec.date_from and rec.date_to:
                domain += [
                    ('move_id.date','>=',rec.date_from.strftime("%Y-%m-%d")),
                    ('move_id.date','<=',rec.date_to.strftime("%Y-%m-%d")),
                ]

            if account_ids:
                domain += [('account_id.id','in',account_ids._origin.mapped('id'))]
            if rec.team_id:
                domain += [('partner_id.team_id.id','=',rec.team_id.id)]
            elif partner_ids:
                domain += [('partner_id.id','in',partner_ids.mapped('id'))]
            
            rec.domain = domain

    def action_confirm(self):
        aml_env = self.env["account.move.line"].sudo()
        for rec in self.sudo():
            if rec.domain:
                rec.write({
                    "aml_ids": False,
                    "am_ids": False,
                })
                domain = ast.literal_eval(rec.domain)
                aml_ids = aml_env.search(domain)
                rec.write(
                    {
                        "aml_ids": [(6, 0, aml_ids.ids)],
                        "am_ids": [(6, 0, aml_ids.mapped("move_id").ids)],
                    }
                )
                if rec.type == 'cong_no_phai_thu':
                    rec.write({
                        "line1_ids": False,
                        "line1_nt_ids": False,
                        "line1_th_ids": False,
                        "line1_th_nt_ids": False,
                    })
                    rec.get_row_data_chi_tiet_cong_no_phai_thu()
                    rec._compute_line('chi-tiet')
                    rec._compute_end()
                    rec.get_row_data_tong_hop_cong_no_phai_thu()
                    rec._compute_line('tong-hop')
                elif rec.type == 'cong_no_phai_tra':
                    rec.write({
                        "line2_ids": False,
                        "line2_nt_ids": False,
                        "line2_th_ids": False,
                        "line2_th_nt_ids": False,
                    })
                    rec.get_row_data_chi_tiet_cong_no_phai_tra()
                    rec._compute_line('chi-tiet')
                    rec._compute_end()
                    rec.get_row_data_tong_hop_cong_no_phai_tra()
                    rec._compute_line('tong-hop')

    def action_view_tree(self):
        # action_chi_tiet_cong_no_phai_thu_view_tree
        # action_chi_tiet_cong_no_phai_tra_view_tree
        # action_tong_hop_cong_no_phai_thu_view_tree
        # action_tong_hop_cong_no_phai_tra_view_tree
        # action_tong_hop_cong_no_phai_thu_nt_view_tree
        # action_tong_hop_cong_no_phai_tra_nt_view_tree
        # action_chi_tiet_cong_no_phai_tra_nt_view_tree
        # action_chi_tiet_cong_no_phai_thu_nt_view_tree
        ctx = self.env.context
        lines = self.env['ccv.debt.report.line1']
        action_name = 'action_'
        if self.type == 'cong_no_phai_thu':
            if ctx.get('type',False) == 'chi_tiet' and ctx.get('nt',False) == 'nt':
                lines = self.line1_nt_ids
            elif ctx.get('type',False) == 'chi_tiet':
                lines = self.line1_ids
            elif ctx.get('type',False) == 'tong_hop' and ctx.get('nt',False) == 'nt':
                lines = self.line1_th_nt_ids
            elif ctx.get('type',False) == 'tong_hop':
                lines = self.line1_th_ids
        elif self.type == 'cong_no_phai_tra':
            if ctx.get('type',False) == 'chi_tiet' and ctx.get('nt',False) == 'nt':
                lines = self.line2_nt_ids
            elif ctx.get('type',False) == 'chi_tiet':
                lines = self.line2_ids
            elif ctx.get('type',False) == 'tong_hop' and ctx.get('nt',False) == 'nt':
                lines = self.line2_th_nt_ids
            elif ctx.get('type',False) == 'tong_hop':
                lines = self.line2_th_ids
        action_name += ctx.get('type',"") + "_" + self.type + "_" + ctx.get('nt',"") + ("_view_tree" if ctx.get('nt',False) else "view_tree")
        action = self.env['ir.actions.act_window']._for_xml_id('ccv_bao_cao_cong_no.%s' % action_name)
        action['domain'] = [('id','in',lines.ids)]
        return action

    def action_open_account_move(self):
        domain = [('id','in', self.am_ids.ids)]
        return {
            'name': "Hóa đơn",
            'res_model': "account.move",
            'view_mode': 'tree,form',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'domain' : domain or []
        }

    def action_open_account_move_line(self):
        domain = [('id','in', self.aml_ids.ids)]
        return {
            'name': "Hóa đơn",
            'res_model': "account.move.line",
            'view_mode': 'tree',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'domain' : domain or []
        }

    def action_change_state(self):
        for rec in self:
            rec.state = "new" if rec.state == "locked" else "locked"

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

    ###########################################
    ###############  RUN QUERY  ###############
    ###########################################

    def get_dk_w_partner(self,partner_id,account_id,line_name):
        if self.parent_id:
            line_ids = getattr(self.parent_id, line_name).filtered(lambda l:l.partner_id == partner_id and l.account_id == account_id)
            return line_ids
        return self.env[getattr(getattr(self.parent_id, line_name),'_name')]

    def get_row_data_chi_tiet_cong_no_phai_thu(self):
        for rec in self.sudo():
            if rec.aml_ids:
                aml_ids = rec.aml_ids
                partner_ids = self.env['res.partner'].sudo()
                if rec.parent_id:
                    partner_ids |= rec.parent_id.line1_th_ids.mapped('partner_id')
                    aml_ids += rec.parent_id.aml_ids
                if rec.report_type == '1':
                    aml_ids = aml_ids.filtered(lambda l:l.partner_id == rec.partner_id)
                elif rec.report_type == 'team':
                    aml_ids = aml_ids.filtered(lambda l:l.partner_id.team_id == rec.team_id)

                partner_ids |= aml_ids.mapped("partner_id")
                account_ids = aml_ids.mapped("account_id")

                data = []
                # cấn trừ: xét tài khoản phải thu + phải trả
                # tất toán: 711, 811
                for partner_id in partner_ids:
                    for account_id in account_ids:
                        data_ps = []
                        move_line_ids = rec.am_ids.line_ids.filtered(lambda l: l.partner_id == partner_id)
                        move_ids = move_line_ids.mapped('move_id').sorted("date")
                        dk = self.get_dk_w_partner(partner_id,account_id,'line1_th_ids')
                        dk_credit = dk.end_credit
                        dk_debit = dk.end_debit
                        dk_credit_nt = dk.end_credit_nt
                        dk_debit_nt = dk.end_debit_nt
                        arr_dk = [{
                            "parent_id": rec.id,
                            "partner_id":partner_id.id,
                            "account_id": account_id.id,
                            "note": 'Số dư đầu kỳ',
                            "end_debit": dk_debit,
                            "end_credit": dk_credit,
                            "end_debit_nt": dk_debit_nt,
                            "end_credit_nt": dk_credit_nt,
                            "type_line": 'chi_tiet',
                        }]
                        for move_id in move_ids:
                            line_ids = move_id.line_ids
                            line_count = len(line_ids)
                            line_src = line_ids.filtered(lambda l:l.account_id == account_id and l.partner_id == partner_id)
                            if line_src:
                                new_line_src = line_src.filtered(lambda l:l.debit or l.credit)
                                if not new_line_src:
                                    line_src = line_src[0]
                                else:
                                    line_src = new_line_src[0]
                            is_credit = line_src.credit > 0
                            if is_credit:
                                ctp_ids = move_id.ctp_ids.filtered(lambda l:l.cr_aml_id == line_src)
                            else:
                                ctp_ids = move_id.ctp_ids.filtered(lambda l:l.dr_aml_id == line_src)
                            line_filter = line_ids.filtered(lambda l:
                                l.partner_id == partner_id
                                and l.account_id.account_type not in ('asset_receivable', 'liability_payable', 'equity')
                                and l.account_id and l.account_id.code
                                and '711' not in l.account_id.code
                                and '811' not in l.account_id.code
                                and '9999' not in l.account_id.code)
                            count_line = len(line_filter)
                            not_account_ids = (line_ids - line_src).filtered(lambda l:l.account_id).mapped('account_id').filtered(lambda l: l.account_type in ('equity') or (l.code and ('711' in l.code or '811' in l.code or '9999' in l.code)))
                            if count_line == 0 and not_account_ids:
                                if line_src.debit or line_src.credit:
                                    obj = {
                                        "parent_id":rec.id,
                                        "partner_id":partner_id.id,
                                        "date": line_src.move_id.date,
                                        "move_id": line_src.move_id.id,
                                        "reference": line_src.get_reference(line_src,line_src),
                                        "note": line_src.name,
                                        "account_id": account_id.id,
                                        "account_dest_id": line_src.account_id.id,
                                        "ps_debit": line_src.debit,
                                        "ps_credit": line_src.credit,
                                        "product_uom_quantity": line_src.quantity if not move_id.payment_id else 0,
                                        "price_unit": line_src.price_unit,
                                        "uom_id": line_src.product_uom_id.id,
                                        "currency_id": line_src.currency_id.id,
                                        "default_code": line_src.product_id.default_code,
                                        "product_id": line_src.product_id.id,
                                        "order_id": line_src.sale_line_ids[0].order_id.id if line_src.sale_line_ids.order_id else False,
                                        "type_line": 'chi_tiet',
                                    }
                                    if rec.is_currency:
                                        obj.update({
                                            "ps_debit_nt": self.get_conversion_rate(abs(line_src.amount_currency), line_src.currency_id, move_id.date) if line_src.debit != 0 else 0,
                                            "ps_credit_nt": self.get_conversion_rate(abs(line_src.amount_currency), line_src.currency_id, move_id.date) if line_src.credit != 0 else 0,
                                        })
                                    data_ps.append(obj)
                                continue
                            for line in move_id.line_ids:
                                can_run = False
                                cur_line = self.env['account.move.line'].sudo()
                                if line.account_id != account_id:
                                    if line_count == 2:
                                        cur_line = line
                                        can_run = True
                                    elif is_credit:
                                        cur_line = ctp_ids.filtered(lambda l:l.dr_aml_id == line)
                                        if cur_line:
                                            cur_line = cur_line.dr_aml_id
                                        can_run = True
                                    else:
                                        cur_line = ctp_ids.filtered(lambda l:l.cr_aml_id == line)
                                        if cur_line:
                                            cur_line = cur_line.cr_aml_id
                                        can_run = True
                                if not can_run or not cur_line:
                                    continue
                                ps_credit = cur_line.debit
                                ps_debit = cur_line.credit
                                if ps_credit or ps_debit:
                                    obj = {
                                        "parent_id":rec.id,
                                        "partner_id":partner_id.id,
                                        "date": cur_line.move_id.date,
                                        "move_id": cur_line.move_id.id,
                                        "reference": line_src.get_reference(line_src,cur_line),
                                        "note": cur_line.name,
                                        "account_id": account_id.id,
                                        "account_dest_id": cur_line.account_id.id,
                                        "ps_debit": ps_debit,
                                        "ps_credit": ps_credit,
                                        "product_uom_quantity": cur_line.quantity if not move_id.payment_id else 0,
                                        "price_unit": cur_line.price_unit,
                                        "uom_id": cur_line.product_uom_id.id,
                                        "currency_id": cur_line.currency_id.id,
                                        "default_code": cur_line.product_id.default_code,
                                        "product_id": cur_line.product_id.id,
                                        "order_id": cur_line.sale_line_ids[0].order_id.id if cur_line.sale_line_ids.order_id else False,
                                        "type_line": 'chi_tiet',
                                    }
                                    if rec.is_currency:
                                        obj.update({
                                            "ps_debit_nt": self.get_conversion_rate(abs(cur_line.amount_currency), cur_line.currency_id, move_id.date) if cur_line.debit != 0 else 0,
                                            "ps_credit_nt": self.get_conversion_rate(abs(cur_line.amount_currency), cur_line.currency_id, move_id.date) if cur_line.credit != 0 else 0,
                                        })
                                    data_ps.append(obj)
                        
                        if data_ps or (not data_ps and (dk_credit != 0 or dk_debit != 0)):
                            data += arr_dk + data_ps
                if data:
                    rec.line_ids.filtered(lambda l:l.type_line == 'chi_tiet').unlink()
                    rec.line_ids.create(data)

    def get_row_data_tong_hop_cong_no_phai_thu(self):
        for rec in self.sudo():
            if rec.line1_ids:
                data = []

                partner_ids = rec.line1_ids.mapped("partner_id")
                account_ids = rec.line1_ids.mapped("account_id")

                for partner_id in partner_ids:
                    for account_id in account_ids:
                        lines = rec.line1_ids.filtered(lambda l: l.partner_id == partner_id and l.account_id == account_id)
                        dk = self.get_dk_w_partner(partner_id,account_id,'line1_th_ids')
                        dk_credit = dk.end_credit
                        dk_debit = dk.end_debit
                        ps_credit = sum(lines.mapped("ps_credit"))
                        ps_debit = sum(lines.mapped("ps_debit"))
                        sub = (dk_credit + ps_credit) - (ps_debit + dk_debit)
                        end_credit = sub if sub > 0 else 0
                        end_debit = abs(sub) if sub < 0 else 0

                        if rec.is_currency:
                            dk_credit_nt = dk.end_credit_nt
                            dk_debit_nt = dk.end_debit_nt
                            ps_credit_nt = sum(lines.mapped("ps_credit_nt"))
                            ps_debit_nt = sum(lines.mapped("ps_debit_nt"))
                            sub_nt = (dk_credit_nt + ps_credit_nt) - (ps_debit_nt + dk_debit_nt)
                            end_credit_nt = sub_nt if sub_nt > 0 else 0
                            end_debit_nt = abs(sub_nt) if sub_nt < 0 else 0

                        if dk_credit != 0 or dk_debit != 0 or ps_credit != 0 or ps_debit != 0 or end_credit != 0 or end_debit != 0:
                            obj = {
                                "parent_id": rec.id,
                                "partner_id": partner_id.id,
                                "account_id": account_id.id,
                                "start_credit": abs(dk_credit),
                                "start_debit": abs(dk_debit),
                                "ps_credit": abs(ps_credit),
                                "ps_debit": abs(ps_debit),
                                "end_credit": abs(end_credit),
                                "end_debit": abs(end_debit),
                                "partner_name": partner_id.name,
                                "partner_code": partner_id.code_contact,
                                "partner_group": partner_id.team_id.code,
                                "type_line": 'tong_hop',
                                "vat": partner_id.vat,
                                "address": partner_id.full_address_vi,
                            }
                            if rec.is_currency:
                                obj.update({
                                    "start_credit_nt": abs(dk_credit_nt),
                                    "start_debit_nt": abs(dk_debit_nt),
                                    "ps_credit_nt": abs(ps_credit_nt),
                                    "ps_debit_nt": abs(ps_debit_nt),
                                    "end_credit_nt": abs(end_credit_nt),
                                    "end_debit_nt": abs(end_debit_nt),
                                })
                            data.append(obj)
                if data:
                    rec.line_ids.filtered(lambda l:l.type_line == 'tong_hop').unlink()
                    rec.line_ids.create(data)

    def get_row_data_chi_tiet_cong_no_phai_tra(self):
        for rec in self.sudo():
            if rec.aml_ids:
                aml_ids = rec.aml_ids
                partner_ids = self.env['res.partner'].sudo()
                if rec.parent_id:
                    partner_ids |= rec.parent_id.line2_th_ids.mapped('partner_id')
                    aml_ids += rec.parent_id.aml_ids
                if rec.report_type == '1':
                    aml_ids = aml_ids.filtered(lambda l:l.partner_id == rec.partner_id)
                elif rec.report_type == 'team':
                    aml_ids = aml_ids.filtered(lambda l:l.partner_id.team_id == rec.team_id)

                partner_ids |= aml_ids.mapped("partner_id")
                account_ids = aml_ids.mapped("account_id")

                data = []

                for partner_id in partner_ids:
                    for account_id in account_ids:
                        data_ps = []
                        move_line_ids = rec.am_ids.line_ids.filtered(lambda l: l.partner_id == partner_id)
                        move_ids = move_line_ids.mapped('move_id').sorted("date")
                        dk = self.get_dk_w_partner(partner_id,account_id,'line2_th_ids')
                        dk_credit = dk.end_credit
                        dk_debit = dk.end_debit
                        dk_credit_nt = dk.end_credit_nt
                        dk_debit_nt = dk.end_debit_nt
                        arr_dk = [{
                            "parent_id": rec.id,
                            "partner_id":partner_id.id,
                            "account_id": account_id.id,
                            "note": 'Số dư đầu kỳ',
                            "end_debit": dk_debit,
                            "end_credit": dk_credit,
                            "end_debit_nt": dk_debit_nt,
                            "end_credit_nt": dk_credit_nt,
                            "type_line": 'chi_tiet',
                        }]
                        for move_id in move_ids:
                            line_ids = move_id.line_ids
                            line_count = len(line_ids)
                            line_src = line_ids.filtered(lambda l:l.account_id == account_id and l.partner_id == partner_id)
                            if line_src:
                                new_line_src = line_src.filtered(lambda l:l.debit or l.credit)
                                if not new_line_src:
                                    line_src = line_src[0]
                                else:
                                    line_src = new_line_src[0]
                            is_credit = line_src.credit > 0
                            if is_credit:
                                ctp_ids = move_id.ctp_ids.filtered(lambda l:l.cr_aml_id == line_src)
                            else:
                                ctp_ids = move_id.ctp_ids.filtered(lambda l:l.dr_aml_id == line_src)
                            line_filter = line_ids.filtered(lambda l:
                                l.partner_id == partner_id
                                and l.account_id.account_type not in ('asset_receivable', 'liability_payable', 'equity')
                                and l.account_id and l.account_id.code
                                and '711' not in l.account_id.code
                                and '811' not in l.account_id.code
                                and '9999' not in l.account_id.code)
                            count_line = len(line_filter)
                            not_account_ids = (line_ids - line_src).filtered(lambda l:l.account_id).mapped('account_id').filtered(lambda l: l.account_type in ('equity') or (l.code and ('711' in l.code or '811' in l.code or '9999' in l.code)))
                            if count_line == 0 and not_account_ids:
                                if line_src.debit or line_src.credit:
                                    obj = {
                                        "parent_id":rec.id,
                                        "partner_id":partner_id.id,
                                        "date": line_src.move_id.date,
                                        "invoice_date": line_src.move_id.invoice_date,
                                        "move_id": line_src.move_id.id,
                                        "reference": line_src.get_reference(line_src,line_src),
                                        "note": line_src.name,
                                        "account_id": account_id.id,
                                        "account_dest_id": line_src.account_id.id,
                                        "ps_debit": line_src.debit,
                                        "ps_credit": line_src.credit,
                                        "product_uom_quantity": line_src.quantity if not move_id.payment_id else 0,
                                        "uom_id": line_src.product_uom_id.id,
                                        "currency_id": line_src.currency_id.id,
                                        "partner_name": partner_id.name,
                                        "partner_code": partner_id.code_contact,
                                        "partner_group": partner_id.team_id.code,
                                        "type_line": 'chi_tiet',
                                    }
                                    if rec.is_currency:
                                        obj.update({
                                            "ps_debit_nt": self.get_conversion_rate(abs(line_src.amount_currency), line_src.currency_id, move_id.date) if line_src.debit != 0 else 0,
                                            "ps_credit_nt": self.get_conversion_rate(abs(line_src.amount_currency), line_src.currency_id, move_id.date) if line_src.credit != 0 else 0,
                                        })
                                    data_ps.append(obj)
                                continue
                            for line in move_id.line_ids:
                                can_run = False
                                cur_line = self.env['account.move.line'].sudo()
                                countered_amt = 0
                                if line.account_id != account_id:
                                    if line_count == 2:
                                        cur_line = line
                                        countered_amt = cur_line.debit or cur_line.credit
                                        can_run = True
                                    elif is_credit:
                                        cur_line = ctp_ids.filtered(lambda l:l.dr_aml_id == line)
                                        if cur_line:
                                            countered_amt = cur_line.countered_amt
                                            cur_line = cur_line.dr_aml_id
                                        can_run = True
                                    else:
                                        cur_line = ctp_ids.filtered(lambda l:l.cr_aml_id == line)
                                        if cur_line:
                                            countered_amt = cur_line.countered_amt
                                            cur_line = cur_line.cr_aml_id
                                        can_run = True
                                if not can_run or not cur_line:
                                    continue
                                ps_credit = countered_amt if is_credit else 0
                                ps_debit = countered_amt if not is_credit else 0
                                if ps_credit or ps_debit:
                                    obj = {
                                        "parent_id":rec.id,
                                        "partner_id":partner_id.id,
                                        "date": cur_line.move_id.date,
                                        "invoice_date": cur_line.move_id.invoice_date,
                                        "move_id": cur_line.move_id.id,
                                        "reference": line_src.get_reference(line_src,cur_line),
                                        "note": cur_line.name,
                                        "account_id": account_id.id,
                                        "account_dest_id": cur_line.account_id.id,
                                        "ps_debit": ps_debit,
                                        "ps_credit": ps_credit,
                                        "product_uom_quantity": cur_line.quantity if not move_id.payment_id else 0,
                                        "uom_id": cur_line.product_uom_id.id,
                                        "currency_id": cur_line.currency_id.id,
                                        "partner_name": partner_id.name,
                                        "partner_code": partner_id.code_contact,
                                        "partner_group": partner_id.team_id.code,
                                        "type_line": 'chi_tiet',
                                    }
                                    if rec.is_currency:
                                        obj.update({
                                            "ps_debit_nt": self.get_conversion_rate(abs(cur_line.amount_currency), cur_line.currency_id, move_id.date) if cur_line.debit != 0 else 0,
                                            "ps_credit_nt": self.get_conversion_rate(abs(cur_line.amount_currency), cur_line.currency_id, move_id.date) if cur_line.credit != 0 else 0,
                                        })
                                    data_ps.append(obj)
                        
                        if data_ps or (not data_ps and (dk_credit != 0 or dk_debit != 0)):
                            data += arr_dk + data_ps
                if data:
                    rec.line_ids.filtered(lambda l:l.type_line == 'chi_tiet').unlink()
                    rec.line_ids.create(data)

    def get_row_data_tong_hop_cong_no_phai_tra(self):
        for rec in self.sudo():
            if rec.line2_ids:
                data = []

                partner_ids = rec.line2_ids.mapped("partner_id")
                account_ids = rec.line2_ids.mapped("account_id")

                for partner_id in partner_ids:
                    for account_id in account_ids:
                        lines = rec.line2_ids.filtered(lambda l: l.partner_id == partner_id and l.account_id == account_id)
                        dk = self.get_dk_w_partner(partner_id,account_id,'line1_th_ids')
                        dk_credit = dk.end_credit
                        dk_debit = dk.end_debit
                        ps_credit = sum(lines.mapped("ps_credit"))
                        ps_debit = sum(lines.mapped("ps_debit"))
                        sub = (dk_credit + ps_credit) - (ps_debit + dk_debit)
                        end_credit = sub if sub > 0 else 0
                        end_debit = abs(sub) if sub < 0 else 0

                        if rec.is_currency:
                            dk_credit_nt = dk.end_credit_nt
                            dk_debit_nt = dk.end_debit_nt
                            ps_credit_nt = sum(lines.mapped("ps_credit_nt"))
                            ps_debit_nt = sum(lines.mapped("ps_debit_nt"))
                            sub_nt = (dk_credit_nt + ps_credit_nt) - (ps_debit_nt + dk_debit_nt)
                            end_credit_nt = sub_nt if sub_nt > 0 else 0
                            end_debit_nt = abs(sub_nt) if sub_nt < 0 else 0

                        if dk_credit != 0 or dk_debit != 0 or ps_credit != 0 or ps_debit != 0 or end_credit != 0 or end_debit != 0:
                            obj = {
                                "parent_id": rec.id,
                                "partner_id": partner_id.id,
                                "account_id": account_id.id,
                                "start_credit": abs(dk_credit),
                                "start_debit": abs(dk_debit),
                                "ps_credit": abs(ps_credit),
                                "ps_debit": abs(ps_debit),
                                "end_credit": abs(end_credit),
                                "end_debit": abs(end_debit),
                                "partner_name": partner_id.name,
                                "partner_code": partner_id.code_contact,
                                "partner_group": partner_id.team_id.code,
                                "type_line": 'tong_hop',
                                "vat": partner_id.vat,
                                "address": partner_id.full_address_vi,
                            }
                            if rec.is_currency:
                                obj.update({
                                    "start_credit_nt": abs(dk_credit_nt),
                                    "start_debit_nt": abs(dk_debit_nt),
                                    "ps_credit_nt": abs(ps_credit_nt),
                                    "ps_debit_nt": abs(ps_debit_nt),
                                    "end_credit_nt": abs(end_credit_nt),
                                    "end_debit_nt": abs(end_debit_nt),
                                })
                            data.append(obj)
                if data:
                    rec.line_ids.filtered(lambda l:l.type_line == 'tong_hop').unlink()
                    rec.line_ids.create(data)

    def _compute_end(self):
        for rec in self.sudo():
            if rec.type == 'cong_no_phai_thu':
                if rec.is_currency:
                    lines = rec.line1_nt_ids
                else:
                    lines = rec.line1_ids
            elif rec.type == 'cong_no_phai_tra':
                if rec.is_currency:
                    lines = rec.line2_nt_ids
                else:
                    lines = rec.line2_ids
            if lines:
                partner_ids = lines.mapped("partner_id")
                account_ids = lines.mapped("account_id")

                for partner_id in partner_ids:
                    for account_id in account_ids:
                        line_ids = lines.filtered(lambda l: l.partner_id == partner_id and l.account_id == account_id)
                        if line_ids:
                            dk = line_ids[0]
                            sub = dk.end_debit - dk.end_credit
                            sub_nt = dk.end_debit_nt - dk.end_credit_nt
                            for line in (line_ids - dk):
                                sub += line.ps_debit - line.ps_credit
                                if sub < 0:
                                    line.write({'end_credit':abs(sub)})
                                else:
                                    line.write({'end_debit':abs(sub)})
                                sub_nt += line.ps_debit_nt - line.ps_credit_nt
                                if sub < 0:
                                    line.write({'end_credit_nt': abs(sub_nt)})
                                else:
                                    line.write({'end_debit_nt': abs(sub_nt)})

    def get_conversion_rate(self, balance, currency_id, date):
        if currency_id == self.currency_id:
            return balance
        currency_env = self.env['res.currency']
        rate = currency_env._get_conversion_rate(currency_id, self.currency_id, self.env.company, date)
        amount_currency = self.currency_id.round(balance * rate)
        return amount_currency

    def action_view_invoice(self, invoices):
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_partner_shipping_id': self.partner_shipping_id.id,
                'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.name,
            })
        action['context'] = context
        return action
