from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    # payslip_type = fields.Selection(string="Loại phiếu lương", selection=[
    #     ('vp','Lương văn phòng'),
    #     ('sx','Lương sản xuất'),
    #     ('kd','Lương kinh doanh'),
    #     ('all','Xem tất cả'),
    # ])
