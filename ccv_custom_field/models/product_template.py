
from odoo import models, fields,api
from .component import split_string_to_lines

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    split_default_code = fields.Text(string="Mã sản phẩm", compute="_compute_split_default_code")

    @api.depends('default_code')
    def _compute_split_default_code(self):
        for rec in self:
            if rec.default_code:
                rec.split_default_code = split_string_to_lines(rec.default_code,'.',3)
            else:
                rec.split_default_code = False
