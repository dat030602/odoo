from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.partner"

    # identity_card = fields.Char(string="Định danh cá nhân")
    use_identity_card = fields.Selection(string='Xuất hóa đơn', selection=[
        ('vat','Mã số thuế'),
        ('id','Căn cước công dân'),
    ],default='vat')
