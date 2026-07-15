from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def _get_forbidden_fields_write(self):
        """ Returns a list of fields user can't edit when he want to edit a quant in `inventory_mode`."""
        return []