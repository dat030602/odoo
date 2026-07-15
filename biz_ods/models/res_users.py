# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
from datetime import datetime, timedelta
from .ods_component import STATUS_WEBHOOK_VI, DIRECTION_WEBHOOK_VI
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


class ResUsers(models.Model):
    _inherit = 'res.users'

    # is_ods = fields.Boolean(string="Is ODS")
    # ods_extension_id = fields.Many2one(
    #     comodel_name="biz.ods.extension",
    #     string="ODS Extension",
    #     domain=[('ods_user_id', '=', False)]
    # )

    # voip_username = fields.Char(store=True)
