from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class crm_team(models.Model):
    _inherit = "crm.team"

    code = fields.Char(string="Mã đội bán hàng")
