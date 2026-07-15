# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Auth
    ods_service_name = fields.Char(string="Service Name", config_parameter='biz_ods.ods_service_name')
    ods_auth_user = fields.Char(string="Auth User", config_parameter='biz_ods.ods_auth_user')
    ods_auth_key = fields.Char(string="Auth Key", config_parameter='biz_ods.ods_auth_key')

    # Call History
    ods_from_datetime = fields.Datetime(string="From Datetime", config_parameter='biz_ods.ods_from_datetime')
    ods_to_datetime = fields.Datetime(string="To Datetime", config_parameter='biz_ods.ods_to_datetime')