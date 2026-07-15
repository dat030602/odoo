from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_is_zero, float_compare
import logging

_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done_or_cancel(self):
        for ml in self:
            if ml.state in ('done'):
                raise UserError(_('You can not delete product moves if the picking is done. You can only correct the done quantities.'))
