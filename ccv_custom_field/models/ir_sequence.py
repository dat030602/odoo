import ast
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

def _select_nextval(cr, seq_name):
    query = f'SELECT last_value FROM {seq_name}'
    cr.execute(query)
    return cr.fetchone()

class IrSequence(models.Model):
    _inherit = "ir.sequence"

    def get_by_id(self):
        number_next = _select_nextval(self._cr, 'ir_sequence_%03d' % self.id)
        return self.get_next_char(number_next)
