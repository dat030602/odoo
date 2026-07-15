from odoo import api, fields, models, _
import datetime
from odoo.exceptions import ValidationError

class CcvReportDebtSale(models.Model):
    _name = 'ccv.report.debt.sale'
    _description = 'Sổ tổng hợp bán hàng'

    name = fields.Char(string='Tên')
    date_from = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')
    partner_ids = fields.Many2one('res.partner', string='Khách hàng')
    status = fields.Selection([('draft', 'Nháp'), ('locked', 'Đã khóa')], string='Trạng thái', default='draft')

    type_partner = fields.Selection([('1', 'Một khách hàng'), ('team', 'Khu vực'), ('order_state', 'Tỉnh/Thành phố'), ('all', 'Tất cả')], string='Loại khách hàng',default='all')
    partner_id = fields.Many2one('res.partner', string='Khách hàng')
    team_ids = fields.Many2many('crm.team', string='Khu vực')
    order_state_id = fields.Many2one('res.country.state', string='Tỉnh/Thành phố')
    account_id = fields.Many2one('account.account', string='Tài khoản doanh thu')

    line_ids = fields.One2many('ccv.report.debt.sale.line', 'parent_id', string='Chi tiết')
    line_total_ids = fields.One2many('ccv.report.debt.sale.total.line', 'parent_id', string='Tổng hợp')

    # Field cho chữ ký
    voter_id = fields.Many2one('res.users',string="Người lập")
    chief_finance_id = fields.Many2one('res.users',string="Phòng Kế toán")
    lead_sale_id = fields.Many2one('res.users',string="Phòng Kinh doanh")
    director_id  = fields.Many2one('res.users',string="Thủ trưởng đơn vị")

    def default_get(self, fields_list):
        res = super(CcvReportDebtSale, self).default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()
        chief_finance_id = env_params.get_param('ccv_bao_cao.chief_accountant_id', False)
        director_id = env_params.get_param('ccv_bao_cao.director_id', False)
        lead_sale_id = env_params.get_param('ccv_bao_cao_cong_no.lead_sale_id', False)
        account_id = self.env['account.account'].search([('code', 'like', '1311')], limit=1)
        
        res.update({
            'voter_id': self.env.user.id,
            'chief_finance_id': int(chief_finance_id) if chief_finance_id else False,
            'lead_sale_id': int(lead_sale_id) if lead_sale_id else False,
            'director_id': int(director_id) if director_id else False,
            'date_from': datetime.date.today().replace(day=1),
            'date_to': datetime.date.today(),
            'account_id': account_id.id if account_id else False,
        })
        return res

    @api.onchange('date_from', 'date_to')
    def _onchange_datefrom_dateto(self):
        for record in self:
            if record.date_from > record.date_to:
                record.date_to = record.date_from

    def action_lock(self):
        for record in self:
            record.status = 'locked'
    
    def action_unlock(self):
        for record in self:
            record.status = 'draft'
    
    def unlink(self):
        for record in self:
            if record.status == 'locked':
                raise ValidationError(_("Sổ tổng hợp bán hàng đã khóa, không thể xóa"))
        return super().unlink()
    
    def _get_domain_stock_moves(self):
        date_from = datetime.datetime.combine(self.date_from, datetime.datetime.min.time()) - datetime.timedelta(hours=7)
        date_to = datetime.datetime.combine(self.date_to, datetime.datetime.max.time()) - datetime.timedelta(hours=7)
        
        # Get stock moves with same logic as get_lines
        domain = [('sale_line_id', '!=', False), ('location_dest_id.usage', '=', 'customer'), ('state', '=', 'done')]
        if self.date_from:
            domain.append(('picking_id.stock_date_receipt','>=', date_from))
        if self.date_to:
            domain.append(('picking_id.stock_date_receipt','<=', date_to))
        if self.type_partner == '1':
            domain.append(('picking_id.partner_id', '=', self.partner_id.id))
        elif self.type_partner == 'team':
            domain.append(('picking_id.partner_id.team_id', 'in', self.team_ids.ids))
        elif self.type_partner == 'order_state':
            domain.append(('picking_id.partner_id.state_id', '=', self.order_state_id.id))
        return domain

    def _get_stock_moves(self):
        domain = self._get_domain_stock_moves()
        StockMove = self.env['stock.move'].with_context(tz=self.env.user.tz).sudo()
        return StockMove.search(domain)

    def _get_aml(self, date_start, date_end, partner_ids=[], account_id=1013):
        # Build the SELECT clause
        sql = """
            SELECT aml.id, abs(aml.balance) as balance
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

        if partner_ids:
            placeholders = ','.join(['%s'] * len(partner_ids))
            sql += f" AND aml.partner_id IN ({placeholders})"
            params.extend(partner_ids)

        self._cr.execute(sql, tuple(params))
        return self._cr.fetchall()

    def _get_partner_ids(self):
        domain = [('date', '<=', self.date_to)]
        if self.type_partner == '1':
            domain.append(('partner_id', '=', self.partner_id.id))
        elif self.type_partner == 'team':
            domain.append(('partner_id.team_id', 'in', self.team_ids.ids))
        elif self.type_partner == 'order_state':
            domain.append(('partner_id.state_id', '=', self.order_state_id.id))
        return self.env['account.move.line'].sudo().search(domain).mapped('partner_id')

    def action_confirm(self):
        self.ensure_one()
        if self.status == 'locked':
            raise ValidationError(_('Sổ tổng hợp bán hàng đã khóa !!!'))
        
        self.line_ids.unlink()
        self.line_total_ids.unlink()
        partner_ids = self._get_partner_ids()
        amls = self.env['account.move.line'].sudo().browse([aml[0] for aml in self._get_aml(self.date_from, self.date_to, partner_ids.ids)])
        partner_ids = amls.partner_id

        start_debit = self._generate_json_debt_old(partner_ids, datetime.date(1999, 1, 1), self.date_from - datetime.timedelta(days=1))
        detail_vals = []
        total_vals = []

        for partner_id in partner_ids:
            cur_amls = amls.filtered(lambda l:l.partner_id == partner_id)

            if not cur_amls and not start_debit.get(partner_id.id, 0):
                continue

            detail_vals.append({
                'parent_id': self.id,
                'debt_end': start_debit.get(partner_id.id, 0),
                'partner_id': partner_id.id,
                'sequence': 1,
            })

            detail_vals.extend([{
                'parent_id': self.id,
                'aml_id': aml.id,
                'partner_id': aml.partner_id.id,
                'sequence': 2,
            } for aml in cur_amls.filtered(lambda l: l.move_id.move_type not in ['out_invoice', 'out_refund'])])

            move_line_ids = cur_amls.mapped('move_id.line_ids') - cur_amls
            detail_vals.extend([{
                'parent_id': self.id,
                'aml_id': aml.id,
                'partner_id': aml.partner_id.id,
                'sequence': 2,
            } for aml in move_line_ids.filtered(lambda l: l.move_id.move_type in ['out_invoice', 'out_refund'])])

        self.line_ids.create(detail_vals)
        # self.line_ids._compute_aml()
        self._recompute_line_detail()
        self.env.cr.commit()
        for partner_id in partner_ids:
            lines = self.line_ids.filtered(lambda l: l.partner_id == partner_id)
            debt_old = start_debit.get(partner_id.id, 0)
            price_subtotal = sum(lines.mapped('price_subtotal'))
            price_tax = sum(lines.mapped('amount_tax'))
            price_total = sum(lines.mapped('price_total'))
            debt_in = sum(lines.mapped('debt_in'))
            if not(debt_old or price_subtotal or price_tax or price_total or debt_in):
                continue
            total_vals.append({
                'parent_id': self.id,
                'partner_id': partner_id.id,
                'debt_old': debt_old,
                'price_subtotal': price_subtotal,
                'price_tax': price_tax,
                'price_total': price_total,
                'debt_in': debt_in,
            })
        self.line_total_ids.create(total_vals)

    def _recompute_line_detail(self):
        for record in self:
            partner_ids = record.line_ids.mapped('partner_id')
            for partner_id in partner_ids:
                sequence = 2
                line_ids = record.line_ids.filtered(lambda l: l.partner_id == partner_id).sorted(lambda l: (l.sequence, l.date, 0 if l.move_id.payment_id else 1, l.move_id, l.product_id))
                for index, line in enumerate(line_ids):
                    if index == 0:
                        continue
                    line.pre_line = line_ids[index - 1]
                    line.debt_end = line.pre_line.debt_end + line.price_total - line.debt_in
                    line.sequence = sequence
                    sequence += 1

    def _generate_json_debt_old(self, partner_ids, date_start, date_end):
        result = self._get_partner_credit_debit(partner_ids, date_start, date_end)
        res = {}
        for row in result:
            res.update({ row[0]: row[1] - row[2]})
        return res

    def _get_partner_credit_debit(self, partner_ids, date_start, date_end, account_id = 1013,is_nt=False):
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

        if partner_ids:
            placeholders = ','.join(['%s'] * len(partner_ids))
            sql += f" AND aml.partner_id IN ({placeholders})"
            params.extend(partner_ids.ids)

        sql += " GROUP BY aml.partner_id"
        sql += " HAVING sum(aml.debit) > 0 OR sum(aml.credit) > 0"
        sql += " ORDER BY aml.partner_id"
        self._cr.execute(sql, tuple(params))
        result = self._cr.fetchall()
        return result
