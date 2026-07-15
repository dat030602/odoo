import ast
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_create_orderpoint_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo cảnh báo tồn kho',
            'res_model': 'create.orderpoint.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'active_model': 'product.template',
            },
        }
