from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class InterestRateYear(models.Model):
    _name = 'interest.rate.year'
    _description = 'Lãi suất theo năm'
    _order = 'year desc'

    name = fields.Char("Tên", compute="_compute_name_interest")
    year = fields.Selection(
        selection=[(str(y), str(y)) for y in range(2000, 2100)],
        string='Năm', required=True, unique=True
    )
    rate = fields.Float(string='Lãi suất (%)', required=True)
    type = fields.Selection(string='Loại', required=True, selection=[
        ('1','Lãi suất trả chậm'),
        ('2','Lãi phạt'),
    ])
    num_of_date = fields.Integer(string='Số ngày phạt')

    @api.depends('year', 'rate', 'type')
    def _compute_name_interest(self):
        for rec in self:
            label = 'Lãi suất trả chậm' if rec.type == '1' else 'Lãi phạt'
            rate_display = f"{rec.rate or 0:.2f}%"
            rec.name = f"{label} - {rec.year} - {rate_display}"
