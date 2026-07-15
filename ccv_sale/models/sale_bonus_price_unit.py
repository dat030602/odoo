from odoo import models, fields, api
import datetime
import logging

_logger = logging.getLogger(__name__)


class SaleBonusPriceUnit(models.Model):
    _name = "sale.bonus.price.unit"
    _description = "Quỹ dự phòng"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Tên", tracking=True)
    team_id = fields.Many2one('crm.team',string="Đội bán hàng", tracking=True)
    categ_ids = fields.Many2many('product.category',string="Danh mục sản phẩm", tracking=True)
    partner_ids = fields.Many2many('res.partner',string="Khách hàng", tracking=True)
    amount = fields.Monetary(string="Số tiền", currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency',string="Tiền tệ", tracking=True)
    date_from = fields.Date(string="Từ ngày", tracking=True)
    date_to = fields.Date(string="Đến ngày", tracking=True)
    bonus_history_line_ids = fields.One2many('sale.bonus.history.line', 'parent_id', string="Lịch sử quỹ dự phòng")

    bonus_default_id = fields.Many2one('sale.bonus.price.unit', string="Quỹ dự phòng mặc định", tracking=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['date_from'] = datetime.date.today()
        res['currency_id'] = self.env.user.company_id.currency_id.id
        return res

    def _cron_create_bonus_history_line(self):
        bonus_ids = self.search([('date_from', '!=', False)])
        for rec in bonus_ids:
            date_from = rec.date_from
            date_to = rec.date_to
            if not date_to:
                date_to = (datetime.date.today().replace(day=1) - datetime.timedelta(days=1))
            month_from = date_from.month
            year_from = date_from.year
            month_to = date_to.month
            year_to = date_to.year
            while month_from <= month_to and year_from <= year_to:
                bonus_history_line_ids = rec.bonus_history_line_ids.search([('date_month', '=', str(month_from)),('date_year', '=', str(year_from)),('parent_id', '=', rec.id)])
                if not bonus_history_line_ids:
                    bonus_history_line_ids = self.env['sale.bonus.history.line'].create({
                        'parent_id': rec.id,
                        'date_month': str(month_from),
                        'date_year': str(year_from),
                    })
                bonus_history_line_ids._onchange_date_month_date_year()
                month_from += 1
                if month_from > 12:
                    month_from = 1
                    year_from += 1
