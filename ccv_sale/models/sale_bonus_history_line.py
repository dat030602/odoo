from odoo import models, fields, api
import datetime
import logging
import calendar

_logger = logging.getLogger(__name__)


class SaleBonusHistoryLine(models.Model):
    _name = "sale.bonus.history.line"
    _description = "Lịch sử quỹ dự phòng"
    _order = 'parent_id,id'

    parent_id = fields.Many2one('sale.bonus.price.unit',string="Quỹ dự phòng")
    amount = fields.Monetary(string="Số tiền", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency',string="Tiền tệ", default=lambda self: self.env.company.currency_id)
    date_month = fields.Selection([
        ('1', 'Tháng 1'),
        ('2', 'Tháng 2'),
        ('3', 'Tháng 3'),
        ('4', 'Tháng 4'),
        ('5', 'Tháng 5'),
        ('6', 'Tháng 6'),
        ('7', 'Tháng 7'),
        ('8', 'Tháng 8'),
        ('9', 'Tháng 9'),
        ('10', 'Tháng 10'),
        ('11', 'Tháng 11'),
        ('12', 'Tháng 12')], string="Tháng")
    date_year = fields.Selection([
        ('2025', '2025'),
        ('2026', '2026'),
        ('2027', '2027'),
        ('2028', '2028'),
        ('2029', '2029'),
        ('2030', '2030')], string="Năm")

    @api.onchange('date_month', 'date_year')
    def _onchange_date_month_date_year(self):
        self.ensure_one()
        for rec in self:
            date_start = '%s-%s-01 00:00:00' % (rec.date_year, rec.date_month)
            last_day = calendar.monthrange(int(rec.date_year), int(rec.date_month))[1]
            date_end = '%s-%s-%02d 23:59:59' % (rec.date_year, rec.date_month, last_day)

            pk_ids = self.env['stock.picking'].search([('stock_date_receipt', '>=', date_start),('stock_date_receipt', '<=', date_end),('state', '=', 'done'),('sale_id.bonus_price_id', '=', rec.parent_id.id)])

            amount = 0
            for pk in pk_ids:
                for line in pk.move_ids.filtered(lambda x: x.quantity_done > 0):
                    amount += line.quantity_done * line.sale_line_id.price_unit_bonus
            rec.amount = amount

    def view_detail(self):
        self.ensure_one()
        date_start = '%s-%s-01 00:00:00' % (self.date_year, self.date_month)
        last_day = calendar.monthrange(int(self.date_year), int(self.date_month))[1]
        date_end = '%s-%s-%02d 23:59:59' % (self.date_year, self.date_month, last_day)

        pk_ids = self.env['stock.picking'].search([('stock_date_receipt', '>=', date_start),('stock_date_receipt', '<=', date_end),('state', '=', 'done'),('sale_id.bonus_price_id', '=', self.parent_id.id)])
        sol_ids = pk_ids.mapped('sale_id')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Đơn hàng',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id', 'in', sol_ids.ids)],
        }
