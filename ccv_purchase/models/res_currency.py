from odoo import fields, models, api
from odoo import tools

import logging
_logger = logging.getLogger(__name__)

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    rounding_threshold = fields.Float(
        string='Ngưỡng làm tròn',
        default=0,
        help='Ngưỡng phần thập phân tối thiểu để áp dụng làm tròn. '
             'Ví dụ: 0.7 cho 2 chữ số thập phân, 0.07 cho 3 chữ số thập phân.',
        digits=(16, 5),
    )

    rounding_method = fields.Selection(string='Làm tròn', required=True,
        selection=[('UP', 'Lên'), ('DOWN', 'Xuống'), ('HALF-UP', 'HALF-UP')],
        default='HALF-UP', help='The tie-breaking rule used for float rounding operations')

    @api.model
    def should_apply_rounding(self, amount):
        self.ensure_one()
        if self.rounding_method == 'HALF-UP':
            return True
        decimal_places = self.decimal_places + 1
        threshold = self.rounding_threshold
        fractional = abs(amount) - abs(int(amount))
        fractional = round(fractional, decimal_places)
        return fractional > threshold

    def round(self, amount):
        """Return ``amount`` rounded  according to ``self``'s rounding rules.

           :param float amount: the amount to round
           :return: rounded float
        """
        self.ensure_one()
        if self.should_apply_rounding(amount):
            return tools.float_round(amount, precision_rounding=self.rounding, rounding_method=self.rounding_method)
        return amount
    