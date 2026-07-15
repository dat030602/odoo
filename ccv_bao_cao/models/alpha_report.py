from odoo import models, fields, api
import logging
from odoo.exceptions import UserError
import datetime
import psycopg2

_logger = logging.getLogger(__name__)

ALL_TYPE = {
    "tong_hop_cong_no_phai_thu": ("Tổng hợp công nợ phải thu", 'beta.report.line1', 'beta_line1_ids'),
    "tong_hop_cong_no_phai_tra": ("Tổng hợp công nợ phải trả", 'beta.report.line2', 'beta_line2_ids'),
    "tong_hop_cong_no_phai_thu_usd": ("Tổng hợp công nợ phải thu USD", 'beta.report.line3', 'beta_line3_ids'),
    "tong_hop_cong_no_phai_tra_usd": ("Tổng hợp công nợ phải trả USD", 'beta.report.line4', 'beta_line4_ids'),
    "chi_tiet_cong_no_phai_tra_usd": ("Chi tiết công nợ phải trả USD", 'beta.report.line5', 'beta_line5_ids'),
    "chi_tiet_cong_no_phai_thu_usd": ("Chi tiết công nợ phải thu USD", 'beta.report.line6', 'beta_line6_ids'),
    "danh_sach_chi_tien_von_tu_co": ("Danh sách chi tiền (thu tiền) khách hàng/Nhà cung cấp", 'beta.report.line7', 'beta_line7_ids'),
    "chi_tiet_cong_no_nhan_vien": ("Chi tiết công nợ nhân viên", 'alpha.report.line3', 'line3_ids'),
}

ALL_TYPE_NT = [
    "tong_hop_cong_no_phai_thu_usd",
    "tong_hop_cong_no_phai_tra_usd",
    "chi_tiet_cong_no_phai_tra_usd",
    "chi_tiet_cong_no_phai_thu_usd",
]

contrainst = {
    'account_id': "Tài khoản",
    'date_from': "Ngày bắt đầu",
    'date_to': "Ngày kết thúc",
    'partner_id': "Khách hàng",
}
class AlphaReport(models.TransientModel):
    _inherit = "alpha.report"

    type = fields.Selection(selection_add=[(key, value[0])for key,value in ALL_TYPE.items()])

    beta_line1_ids = fields.One2many("beta.report.line1",'parent_id', string="Tong hop cong no phai thu")
    beta_line2_ids = fields.One2many("beta.report.line2",'parent_id', string="Tong hop cong no phai tra")
    beta_line3_ids = fields.One2many("beta.report.line3",'parent_id', string="Tong hop cong no phai thu USD")
    beta_line4_ids = fields.One2many("beta.report.line4",'parent_id', string="Tong hop cong no phai tra USD")
    beta_line5_ids = fields.One2many("beta.report.line5",'parent_id', string="Chi tiết công nợ phai tra USD")
    beta_line6_ids = fields.One2many("beta.report.line6",'parent_id', string="Chi tiết cong no phai thu USD")
    beta_line7_ids = fields.One2many("beta.report.line7",'parent_id', string="Danh sách chi tiền vốn tự có")

    partner_payment_type = fields.Selection(string="Loại đối tác", selection=[
        ('customer','Khách hàng'),
        ('supplier','Nhà cung cấp'),
    ],default='customer')

    currency_id         = fields.Many2one("res.currency", string="Tiền tệ")
    is_foreign_currency = fields.Boolean("Ngoại tệ", compute="_compute_foreign_currency")
    is_sale = fields.Boolean(default=False)
    sale_allowed_team_ids = fields.Many2many("crm.team", string="Allowed Teams", compute="_compute_sale_allowed_team_ids")
    check_have_mount = fields.Boolean(string="Có số dư", default=False)

    @api.depends('is_sale')
    def _compute_sale_allowed_team_ids(self):
        for record in self:
            if record.is_sale:
                record.sale_allowed_team_ids = record._get_sale_allowed_teams()
            else:
                record.sale_allowed_team_ids = False

    def _get_sale_team_domain(self):
        """Return onchange domain dict to restrict team_id dropdown for sale reports."""
        if self.is_sale:
            allowed_teams = self._get_sale_allowed_teams()
            return {'domain': {'team_id': [('id', 'in', allowed_teams.ids)]}}
        return {}

    def _get_partner_team(self, partner):
        return partner.team_id or partner.commercial_partner_id.team_id

    def _get_report_team_ids(self, allowed_team_ids=False):
        if not self.is_sale:
            return self.team_id
        allowed_team_ids = allowed_team_ids or self._get_sale_allowed_teams()
        if self.team_id and self.team_id in allowed_team_ids:
            return self.team_id
        return allowed_team_ids

    def _ensure_sale_team_id(self):
        if not self.is_sale:
            return
        allowed_teams = self._get_sale_allowed_teams()
        if self.report_type == 'team' and (not self.team_id or self.team_id not in allowed_teams):
            self.team_id = allowed_teams[:1]


    @api.depends('type','report_type')
    def _compute_partner_state(self):
        if self.type in ALL_TYPE.keys():
            if self.type in ('chi_tiet_cong_no_phai_tra_usd','chi_tiet_cong_no_phai_thu_usd'):
                if self.report_type == 'is_many_partner':
                    self.partner_state = '2'
                elif self.report_type in ('team', 'is_all_partner'):
                    self.partner_state = '0'
                else:
                    self.partner_state = '1'
            else:
                if self.report_type == 'is_many_partner':
                    self.partner_state = '2'
                elif self.report_type in ('team', 'is_all_partner'):
                    self.partner_state = '0'
                else:
                    self.partner_state = '0'
        else:
            super(AlphaReport,self)._compute_partner_state()
        
    @api.onchange("report_type")
    def onchange_report_type(self):
        self._ensure_sale_team_id()
        team_id = self.team_id
        commerce = int(self.env['ir.config_parameter'].sudo().get_param('ccv_sql.chief_commerce_department_id', self.env.user.id))
        if team_id and team_id.user_id.id == commerce:
            self.chief_dept_id = commerce
        return self._get_sale_team_domain()


    @api.onchange("type")
    def onchange_type(self):
        super(AlphaReport, self).onchange_type()
        if self.type == 'tong_hop_cong_no_phai_thu':
            account_id = self.env['account.account'].search([('code', '=', '13111')], limit=1)
            if len(account_id) > 0:
                self.account_id = account_id.id
            self.report_type = 'is_all_partner'
        elif self.type == 'tong_hop_cong_no_phai_thu_usd':
            account_id = self.env['account.account'].search([('code', '=', '13112')], limit=1)
            if len(account_id) > 0:
                self.account_id = account_id.id
            self.report_type = 'is_all_partner'
        elif self.type == 'chi_tiet_cong_no_phai_thu_usd':
            account_id = self.env['account.account'].search([('code', '=', '13112')], limit=1)
            if len(account_id) > 0:
                self.account_id = account_id.id
            self.report_type = '1'
        elif self.type == 'tong_hop_cong_no_phai_tra':
            account_id = self.env['account.account'].search([('code', '=', '3311')], limit=1)
            if len(account_id) > 0:
                self.account_id = account_id.id
            self.report_type = 'is_all_partner'
        elif self.type == 'tong_hop_cong_no_phai_tra_usd':
            account_id = self.env['account.account'].search([('code', '=', '3312')], limit=1)
            if len(account_id) > 0:
                self.account_id = account_id.id
            self.report_type = 'is_all_partner'
        elif self.type == 'chi_tiet_cong_no_phai_tra_usd':
            account_id = self.env['account.account'].search([('code', '=', '3312')], limit=1)
            if len(account_id) > 0:
                self.account_id = account_id.id
            self.report_type = '1'
        elif self.type == 'danh_sach_chi_tien_von_tu_co':
            currency_id = self.env['res.currency'].search([('name', '=', 'VND')], limit=1)
            if currency_id:
                self.currency_id = currency_id.id
            if self.is_sale:
                self.report_type = 'team'
                self._ensure_sale_team_id()
            else:
                self.report_type = 'is_all_partner'
        elif self.type == 'chi_tiet_cong_no_nhan_vien':
            self.account_id = self.env['account.account'].search([('code', '=', '1411')], limit=1)
            self.report_type = 'is_all_partner'
        return self._get_sale_team_domain()

    @api.depends("type")
    def _compute_foreign_currency(self):
        if self.type in ALL_TYPE_NT:
            self.is_foreign_currency = True
        else:
            self.is_foreign_currency = False

    def _get_sale_allowed_teams(self):
        report_user = self.create_uid or self.env.user
        company_ids = report_user.company_ids.ids
        if report_user.has_group('sales_team.group_sale_salesman_all_leads'):
            return self.env['crm.team'].sudo().search([
                ('active', '=', True),
                '|', ('company_id', '=', False), ('company_id', 'in', company_ids),
            ])
        self.env.cr.execute("""
            SELECT DISTINCT team_id
            FROM (
                SELECT ct.id AS team_id
                FROM crm_team ct
                WHERE ct.active IS TRUE
                  AND (ct.company_id IS NULL OR ct.company_id = ANY(%s))
                  AND ct.user_id = %s

                UNION

                SELECT ctm.crm_team_id AS team_id
                FROM crm_team_member ctm
                JOIN crm_team ct ON ct.id = ctm.crm_team_id
                WHERE ct.active IS TRUE
                  AND (ct.company_id IS NULL OR ct.company_id = ANY(%s))
                  AND ctm.active IS TRUE
                  AND ctm.user_id = %s

                UNION

                SELECT rta.team_id AS team_id
                FROM res_team_assistant_ids rta
                JOIN crm_team ct ON ct.id = rta.team_id
                WHERE ct.active IS TRUE
                  AND (ct.company_id IS NULL OR ct.company_id = ANY(%s))
                  AND rta.assisng_id = %s
            ) allowed_team
            ORDER BY team_id
        """, (company_ids, report_user.id, company_ids, report_user.id, company_ids, report_user.id))
        return self.env['crm.team'].sudo().browse([row[0] for row in self.env.cr.fetchall()])

    def action_open_alpha_sale_report(self):
        res = super().action_open_alpha_sale_report()
        allowed_teams = self._get_sale_allowed_teams()
        res.setdefault('context', {})
        res['context'].update({
            'default_report_type': 'team',
            'default_team_id': allowed_teams[:1].ids if allowed_teams else False,
        })
        return res

    def action_confirm(self):
        try:
            if self.type in ALL_TYPE.keys():
                res = getattr(self, "get_row_data_" + self.type)()
            else:
                res = super(AlphaReport, self).action_confirm()

            if self.check_have_mount:
                for field_name, field in self._fields.items():
                    if field.type == 'one2many':
                        rel_model = self.env[field.comodel_name]
                        if 'end_debit' in rel_model._fields and 'end_credit' in rel_model._fields:
                            lines = getattr(self, field_name)
                            if lines:
                                lines_to_unlink = lines.filtered(lambda l: l.end_debit <= 0 and l.end_credit <= 0)
                                lines_to_unlink.unlink()
            return res
        except psycopg2.OperationalError as e:
            if getattr(e, 'pgcode', '') == '40001' or 'could not serialize access due to concurrent update' in str(e):
                raise UserError("Hệ thống đang có nhiều người cùng truy cập hoặc dữ liệu đang được cập nhật. Vui lòng đợi vài giây rồi nhấn lại nút xác nhận.")
            raise

    def action_view_tree(self):
        if self.type in ALL_TYPE.keys():
            domain = [('parent_id', '=', self.id)]
            action = self.env.ref("ccv_bao_cao.action_%s_beta_view_tree" % self.type).sudo().read()[0]
            action['domain'] = domain
            return action
        return super(AlphaReport, self).action_view_tree()

    def action_print_pdf_report(self):
        if self.type in ALL_TYPE.keys():
            return self.env.ref("ccv_bao_cao.%s_pdf_report" % self.type).report_action(self)
        return super(AlphaReport, self).action_print_pdf_report()
    
    def action_print_xlsx_report(self):
        if self.type in ('chi_tiet_cong_no_phai_thu', 'chi_tiet_cong_no_phai_tra') or \
            self.type in ALL_TYPE.keys():
            return self.env.ref("ccv_bao_cao.%s_xlsx_report" % self.type).report_action(self)
        elif self.type == 'tong_hop_cong_no_nhan_vien':
            return self.env.ref('ccv_bao_cao.tong_hop_cong_no_nhan_vien_xlsx_report').report_action(self)
        return super(AlphaReport, self).action_print_xlsx_report()

    ###########################################
    ###############  RUN QUERY  ###############
    ###########################################

    def _get_debt_report_partners(self, team_ids=False):
        partner_env = self.env['res.partner'].sudo()
        if not self.account_id:
            return partner_env
        params = [self.account_id.id]
        sql = """
            SELECT aml.partner_id
            FROM account_move_line aml
            JOIN res_partner rp ON rp.id = aml.partner_id
            LEFT JOIN res_partner commercial_partner ON commercial_partner.id = rp.commercial_partner_id
            WHERE aml.parent_state = 'posted'
              AND aml.account_id = %s
              AND aml.partner_id IS NOT NULL
        """
        if team_ids is not False:
            if not team_ids:
                return partner_env
            placeholders = ','.join(['%s'] * len(team_ids))
            sql += f" AND COALESCE(rp.team_id, commercial_partner.team_id) IN ({placeholders})"
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
    
    def _get_partner(self):
        partner_ids = self.env['res.partner'].sudo()
        aml_env = self.env['account.move.line'].sudo()
        payment_env = self.env['account.payment'].sudo()
        allowed_team_ids = self.env['crm.team'].sudo()
        if self.is_sale:
            allowed_team_ids = self._get_sale_allowed_teams()
        if self.type == 'chi_tiet_cong_no_nhan_vien':
            partner_ids = self._get_employee().keys()
        elif self.type in (
            'chi_tiet_cong_no_phai_thu',
            'chi_tiet_cong_no_phai_tra',
            'tong_hop_cong_no_phai_thu',
            'tong_hop_cong_no_phai_tra',
            'tong_hop_cong_no_phai_thu_usd',
            'tong_hop_cong_no_phai_tra_usd',
            'chi_tiet_cong_no_phai_tra_usd',
            'chi_tiet_cong_no_phai_thu_usd',
        ):
            if self.report_type == 'is_many_partner':
                partner_ids = self.partner_ids
            elif self.report_type == 'is_all_partner':
                partner_ids = self._get_debt_report_partners()
            elif self.report_type == 'team':
                team_ids = self._get_report_team_ids(allowed_team_ids)
                partner_ids = self._get_debt_report_partners(team_ids=team_ids)
            else:
                partner_ids = self.partner_id
        elif self.type in ('danh_sach_chi_tien_von_tu_co'):
            partner_ids = payment_env.search([]).mapped('partner_id')
            if self.report_type == 'team':
                team_ids = self._get_report_team_ids(allowed_team_ids)
                partner_ids = partner_ids.filtered(lambda l: self._get_partner_team(l) in team_ids)
        if self.is_sale and hasattr(partner_ids, 'filtered'):
            if not allowed_team_ids:
                return self.env['res.partner'].sudo()
            partner_ids = partner_ids.filtered(lambda l: self._get_partner_team(l) in allowed_team_ids)
        return partner_ids

    def _get_partner_total_credit_debit(self, account_id, partner_ids, date_start, date_end, is_nt=False):
        if partner_ids is not None and not partner_ids:
            return []

        # Build the SELECT clause
        sql = """
            SELECT 
            aml.partner_id AS partner_id,
            sum(aml.debit) AS debit,
            sum(aml.credit) AS credit
        """
        
        # Add USD columns if is_nt is True
        if is_nt:
            sql += """
                ,COALESCE(SUM(CASE WHEN aml.debit > 0 
                    THEN function_get_price_w_currency(aml.amount_currency, aml.debit, am.date, aml.currency_id, 2, 1, am.id) 
                    ELSE 0 END), 0) AS debit_nt,
                COALESCE(SUM(CASE WHEN aml.credit > 0 
                    THEN function_get_price_w_currency(aml.amount_currency * -1, aml.credit, am.date, aml.currency_id, 2, 1, am.id) 
                    ELSE 0 END), 0) AS credit_nt
            """
        
        # Add FROM and WHERE clauses
        sql += """
            FROM account_move_line aml
            RIGHT JOIN account_move am ON am.id = aml.move_id
            WHERE am.state = 'posted'
              AND aml.company_id = %s
              AND aml.account_id = %s
        """
        
        params = [self.env.company.id, account_id]

        sql += " AND am.date >= %s AND am.date <= %s"
        params.extend([date_start.strftime("%Y%m%d"), date_end.strftime("%Y%m%d")])

        if partner_ids is not None:
            placeholders = ','.join(['%s'] * len(partner_ids))
            sql += f" AND aml.partner_id IN ({placeholders})"
            params.extend(partner_ids)

        sql += " GROUP BY aml.partner_id"
        sql += " HAVING sum(aml.debit) > 0 OR sum(aml.credit) > 0"
        sql += " ORDER BY aml.partner_id"
        self._cr.execute(sql, tuple(params))
        result = self._cr.fetchall()
        return result

    def _get_partner_credit_debit(self, account_id, partner_ids, date_start, date_end, is_nt=False):
        if partner_ids is not None and not partner_ids:
            return []

        # Build the SELECT clause
        sql = """
            SELECT 
            aml.partner_id AS partner_id,
            aml.id AS id,
            am.date AS date,
            am.id AS move_id,
            aml.quantity AS quantity,
            aml.price_unit AS price_unit,
            aml.debit AS debit,
            aml.credit AS credit,
            aml.invoice_code AS invoice_code,
            aml.invoice_number AS invoice_number,
            aml.date_invoice AS invoice_date,
            CASE WHEN am.note IS NULL THEN aml.name ELSE am.note END AS note
        """
        
        # Add USD columns if is_nt is True
        if is_nt:
            sql += """
                ,COALESCE(CASE WHEN aml.debit > 0 
                    THEN function_get_price_w_currency(aml.amount_currency, aml.debit, am.date, aml.currency_id, 2, 1, am.id) 
                    ELSE 0 END) AS debit_nt,
                COALESCE(CASE WHEN aml.credit > 0 
                    THEN function_get_price_w_currency(aml.amount_currency * -1, aml.credit, am.date, aml.currency_id, 2, 1, am.id) 
                    ELSE 0 END) AS credit_nt
            """
        
        # Add FROM and WHERE clauses
        sql += """
            FROM account_move_line aml
            RIGHT JOIN account_move am ON am.id = aml.move_id
            WHERE aml.parent_state = 'posted'
              AND aml.company_id = %s
              AND aml.account_id = %s
        """
        
        params = [self.env.company.id, account_id]

        sql += " AND am.date >= %s AND am.date <= %s"
        params.extend([date_start.strftime("%Y%m%d"), date_end.strftime("%Y%m%d")])

        if partner_ids is not None:
            placeholders = ','.join(['%s'] * len(partner_ids))
            sql += f" AND aml.partner_id IN ({placeholders})"
            params.extend(partner_ids)

        sql += " ORDER BY aml.partner_id, am.date, am.id"
        self._cr.execute(sql, tuple(params))
        result = self._cr.fetchall()
        return result

    def update_groups_tong_hop_cong_no(self, group, start, ps):
        # Process start data
        for row in start:
            partner_id = row[0]
            group[partner_id] = {
                'start_debit': row[1],
                'start_credit': row[2],
                'start_debit_nt': row[3] if len(row) > 3 else 0,
                'start_credit_nt': row[4] if len(row) > 4 else 0,
                'ps_debit': 0,
                'ps_credit': 0,
                'ps_debit_nt': 0,
                'ps_credit_nt': 0,
            }
        
        for row in ps:
            partner_id = row[0]
            if partner_id in group:
                group[partner_id].update({
                    'ps_debit': row[1],
                    'ps_credit': row[2],
                    'ps_debit_nt': row[3] if len(row) > 3 else 0,
                    'ps_credit_nt': row[4] if len(row) > 4 else 0,
                })
            else:
                group[partner_id] = {
                    'start_debit': 0,
                    'start_credit': 0,
                    'start_debit_nt': 0,
                    'start_credit_nt': 0,
                    'ps_debit': row[1],
                    'ps_credit': row[2],
                    'ps_debit_nt': row[3] if len(row) > 3 else 0,
                    'ps_credit_nt': row[4] if len(row) > 4 else 0,
                }
        return group

    def update_groups_chi_tiet_cong_no(self, group, start, ps):
        for row in start:
            partner_id = row[0]
            if row[1] == row[2]:
                continue
            if partner_id not in group:
                group[partner_id] = []
            group[partner_id].append({
                'partner_id': partner_id,
                'end_debit': row[1],
                'end_credit': row[2],
            })
        for row in ps:
            if row[0] not in group:
                group[row[0]] = [{
                    'partner_id': row[0],
                    'end_debit': 0,
                    'end_credit': 0,
                }]
            invoice_code = row[6] if row[6] is not None else ""
            invoice_number = row[7] if row[7] is not None else ""
            group[row[0]].append({
                'partner_id': row[0],
                'date': row[2],
                'move_id': row[3],
                'ps_debit': row[4],
                'ps_credit': row[5],
                'reference': invoice_code + invoice_number,
                'invoice_date': row[8],
                'note': row[9],
            })
        return group

    def get_row_data_tong_hop_cong_no(self, is_nt=False):
        self = self.sudo()
        partner_ids = self._get_partner()
        group = {}
        start = self._get_partner_total_credit_debit(
            self.account_id.id,
            partner_ids.ids,
            datetime.date(1999, 1, 1),
            self.date_from - datetime.timedelta(days=1),
            is_nt=is_nt
        )
        ps = self._get_partner_total_credit_debit(self.account_id.id, partner_ids.ids, self.date_from, self.date_to, is_nt=is_nt)
        self.update_groups_tong_hop_cong_no(group, start, ps)
        return group

    def get_row_data_chi_tiet_cong_no(self, partner_ids=[]):
        self = self.sudo()
        partner_ids = partner_ids if partner_ids else self._get_partner()
        group = {}
        start = self._get_partner_total_credit_debit(
            self.account_id.id,
            partner_ids,
            datetime.date(1999, 1, 1),
            self.date_from - datetime.timedelta(days=1),
        )
        ps = self._get_partner_credit_debit(self.account_id.id, partner_ids, self.date_from, self.date_to)
        self.update_groups_chi_tiet_cong_no(group, start, ps)
        return group

    def get_row_data_tong_hop_cong_no_phai_thu(self):
        self = self.sudo()
        self.beta_line1_ids.unlink()
        group = self.get_row_data_tong_hop_cong_no()

        # Đầu kỳ
        self.beta_line1_ids = [(0, 0, {
            'parent_id': self.id,
            'partner_id': key,
            'customer_name': self.env['res.partner'].browse(key).name,
            'customer_code': self.env['res.partner'].browse(key).code_contact,
            'customer_group': self._get_partner_team(self.env['res.partner'].browse(key)).code,
            'start_debit': value['start_debit'],
            'start_credit': value['start_credit'],
            'start_debit_nt': value['start_debit_nt'],
            'start_credit_nt': value['start_credit_nt'],
            'ps_debit': value['ps_debit'],
            'ps_credit': value['ps_credit'],
            'ps_debit_nt': value['ps_debit_nt'],
            'ps_credit_nt': value['ps_credit_nt'],
        }) for key, value in group.items() if not(value['start_debit'] == value['start_credit'] and value['ps_debit'] == 0 and value['ps_credit'] == 0)]

        return

    def get_row_data_tong_hop_cong_no_phai_tra(self):
        self = self.sudo()
        self.beta_line2_ids.unlink()
        group = self.get_row_data_tong_hop_cong_no()

        # Đầu kỳ
        self.beta_line2_ids = [(0, 0, {
            'parent_id': self.id,
            'partner_id': key,
            'customer_name': self.env['res.partner'].browse(key).name,
            'customer_code': self.env['res.partner'].browse(key).code_contact,
            'vat': self.env['res.partner'].browse(key).vat or '',
            'address': self.env['res.partner'].browse(key).street or '',
            'start_debit': value['start_debit'],
            'start_credit': value['start_credit'],
            'start_debit_nt': value['start_debit_nt'],
            'start_credit_nt': value['start_credit_nt'],
            'ps_debit': value['ps_debit'],
            'ps_credit': value['ps_credit'],
            'ps_debit_nt': value['ps_debit_nt'],
            'ps_credit_nt': value['ps_credit_nt'],
        }) for key, value in group.items() if not(value['start_debit'] == value['start_credit'] and value['ps_debit'] == 0 and value['ps_credit'] == 0)]

        return

    def get_row_data_tong_hop_cong_no_phai_thu_usd(self):
        self = self.sudo()
        group = self.get_row_data_tong_hop_cong_no(is_nt=True)
        self.beta_line3_ids.unlink()
        # Đầu kỳ
        self.beta_line3_ids = [(0, 0, {
            'parent_id': self.id,
            'partner_id': key,
            'customer_name': self.env['res.partner'].browse(key).name,
            'customer_code': self.env['res.partner'].browse(key).code_contact,
            'vat': self.env['res.partner'].browse(key).vat or '',
            'address': self.env['res.partner'].browse(key).street or '',
            'start_debit': value['start_debit'],
            'start_credit': value['start_credit'],
            'start_debit_nt': value['start_debit_nt'],
            'start_credit_nt': value['start_credit_nt'],
            'ps_debit': value['ps_debit'],
            'ps_credit': value['ps_credit'],
            'ps_debit_nt': value['ps_debit_nt'],
            'ps_credit_nt': value['ps_credit_nt'],
        }) for key, value in group.items() if not(value['start_debit'] == value['start_credit'] and value['ps_debit'] == 0 and value['ps_credit'] == 0)]

        return

    def get_row_data_tong_hop_cong_no_phai_tra_usd(self):
        self = self.sudo()
        group = self.get_row_data_tong_hop_cong_no(is_nt=True)
        self.beta_line4_ids.unlink()
        # Đầu kỳ
        self.beta_line4_ids = [(0, 0, {
            'parent_id': self.id,
            'partner_id': key,
            'customer_name': self.env['res.partner'].browse(key).name,
            'customer_code': self.env['res.partner'].browse(key).code_contact,
            'vat': self.env['res.partner'].browse(key).vat or '',
            'address': self.env['res.partner'].browse(key).street or '',
            'start_debit': value['start_debit'],
            'start_credit': value['start_credit'],
            'start_debit_nt': value['start_debit_nt'],
            'start_credit_nt': value['start_credit_nt'],
            'ps_debit': value['ps_debit'],
            'ps_credit': value['ps_credit'],
            'ps_debit_nt': value['ps_debit_nt'],
            'ps_credit_nt': value['ps_credit_nt'],
        }) for key, value in group.items() if not(value['start_debit'] == value['start_credit'] and value['ps_debit'] == 0 and value['ps_credit'] == 0)]

        return

    def get_row_data_chi_tiet_cong_no_phai_tra_usd(self):
        # self.check_invalid(['date_from', 'date_to', 'account_id', 'partner_id'])
        partner_ids = self._get_partner()
        self.env.cr.execute("delete from beta_report_line5 where parent_id = %s;" % self.id)
        query = ";".join(["select * from function_chi_tiet_cong_no_phai_tra_usd('%s','%s',%s,%s,%s,%s,%s)" \
            % (self.date_from, self.date_to, self.env.user.company_id.id, self.account_id.id, partner_id.id, self.id,False if self.partner_state in ('0','2') else True)
            for partner_id in partner_ids])
        self.env.cr.execute(query)
        result = self.env.cr.fetchall()
        self.beta_line5_ids._compute_end_balance()
        self.beta_line5_ids._compute_end_balance_nt()
        return result

    def get_row_data_chi_tiet_cong_no_phai_thu_usd(self):
        # self.check_invalid(['date_from', 'date_to', 'account_id', 'partner_id'])
        partner_ids = self._get_partner()
        self.env.cr.execute("delete from beta_report_line6 where parent_id = %s;" % self.id)
        query = ";".join(["select * from function_chi_tiet_cong_no_phai_thu_usd('%s','%s',%s,%s,%s,%s,%s)" \
            % (self.date_from, self.date_to, self.env.user.company_id.id, self.account_id.id, partner_id.id, self.id,False if self.partner_state in ('0','2') else True)
            for partner_id in partner_ids])
        self.env.cr.execute(query)
        result = self.env.cr.fetchall()
        self.beta_line6_ids._compute_end_balance()
        self.beta_line6_ids._compute_end_balance_nt()
        return result
    
    def get_row_data_danh_sach_chi_tien_von_tu_co(self):
        # self.check_invalid(['date_from', 'date_to', 'account_id', 'partner_id'])
        query = "select * from function_danh_sach_chi_tien_von_tu_co(%s,%s,%s,%s,%s,%s,%s,%s)" 
        self.env.cr.execute(query,
        (self.date_from
            , self.date_to
            , self.partner_payment_type
            , 'outbound' if self.partner_payment_type == 'supplier' else 'inbound'
            , self.currency_id.id
            , self.env.user.id
            , self.id
            , self._get_partner().ids)
        )
        result = self.env.cr.fetchall()
        return result

    def _get_employee(self):
        self = self.with_context(active_test=False)
        employee_ids = self.employee_id or self.env['hr.employee'].search([('company_id', '=', self.env.company.id)])
        group = {}
        for employee in employee_ids.filtered(lambda e: e.user_id.partner_id):
            group[employee.user_id.partner_id] = employee
        return group

    def get_row_data_chi_tiet_cong_no_nhan_vien(self):
        self = self.sudo().with_context(active_test=False)
        self.line3_ids.unlink()
        
        partner_records = self._get_partner()
        if not partner_records:
            return
        
        partner_ids = tuple(partner_records.ids) if hasattr(partner_records, 'ids') else tuple(p.id for p in partner_records)
        if not partner_ids:
            return

        # Get Start Balance
        start_data = {}
        self.env.cr.execute("""
            SELECT aml.partner_id, sum(aml.debit) as start_debit, sum(aml.credit) as start_credit
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.account_id = %s
              AND aml.partner_id IN %s
              AND am.state = 'posted'
              AND am.date < %s
            GROUP BY aml.partner_id
        """, (self.account_id.id, partner_ids, self.date_from))
        for row in self.env.cr.dictfetchall():
            start_data[row['partner_id']] = {
                'start_debit': row['start_debit'] or 0.0,
                'start_credit': row['start_credit'] or 0.0
            }

        # Get PS Lines
        self.env.cr.execute("""
            SELECT 
                aml.partner_id,
                aml.id as aml_id,
                am.id as move_id,
                am.date as date,
                am.name as reference,
                aml.name as note,
                aml.debit as debit,
                aml.credit as credit,
                (
                    SELECT account_id 
                    FROM account_move_line 
                    WHERE move_id = am.id AND id != aml.id 
                      AND (debit > 0 OR credit > 0)
                    LIMIT 1
                ) as account_dest_id
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.account_id = %s
              AND aml.partner_id IN %s
              AND am.state = 'posted'
              AND (am.date >= %s AND am.date <= %s)
            ORDER BY aml.partner_id, am.date, aml.id
        """, (self.account_id.id, partner_ids, self.date_from, self.date_to))
        ps_lines = self.env.cr.dictfetchall()
            
        lines_to_create = []
        ps_by_partner = {}
        for row in ps_lines:
            ps_by_partner.setdefault(row['partner_id'], []).append(row)
            
        for p_id in partner_ids:
            start = start_data.get(p_id, {'start_debit': 0.0, 'start_credit': 0.0})
            lines = ps_by_partner.get(p_id, [])
            
            if start['start_debit'] == 0.0 and start['start_credit'] == 0.0 and not lines:
                continue
                
            balance = start['start_debit'] - start['start_credit']
            
            # Start row
            start_debit = balance if balance > 0 else 0.0
            start_credit = -balance if balance < 0 else 0.0
            lines_to_create.append((0, 0, {
                'partner_id': p_id,
                'reference': 'Số dư đầu kỳ',
                'account_id': self.account_id.id,
                'start_debit': start_debit,
                'start_credit': start_credit,
                'end_debit': start_debit,
                'end_credit': start_credit,
                'parent_id': self.id,
            }))
            
            for row in lines:
                balance += (row['debit'] - row['credit'])
                end_debit = balance if balance > 0 else 0.0
                end_credit = -balance if balance < 0 else 0.0
                
                lines_to_create.append((0, 0, {
                    'partner_id': p_id,
                    'date': row['date'],
                    'move_id': row['move_id'],
                    'reference': row['reference'],
                    'note': row['note'],
                    'account_id': self.account_id.id,
                    'account_dest_id': row['account_dest_id'],
                    'debit': row['debit'],
                    'credit': row['credit'],
                    'end_debit': end_debit,
                    'end_credit': end_credit,
                    'parent_id': self.id,
                }))
                
        if lines_to_create:
            self.write({'line3_ids': lines_to_create})
            
        return
