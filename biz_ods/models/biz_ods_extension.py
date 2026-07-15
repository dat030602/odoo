# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from datetime import datetime, timedelta
from .ods_component import ODS, ODS_PAGE_SIZE, DEFAULT_ODS_DATETIME_FORMAT
from odoo import fields, models, api
from odoo.tools.translate import _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class Extension(models.Model):
    _name = 'biz.ods.extension'
    _description = 'Extension'
    _rec_name = 'ods_id'

    ods_id = fields.Char(string="ID")
    ods_data = fields.Char(string="Data")
    ods_user_id = fields.Many2one(comodel_name="res.users", string="User", domain="[('voip_username', '=', False)]")
    ods_partner_id = fields.Many2one(comodel_name='res.partner', string="Partner", related="ods_user_id.partner_id")

    @api.constrains('ods_user_id')
    def _check_ods_user_id(self):
        for record in self:
            is_ods_administrator = self.env.user.has_group('biz_ods.biz_ods_group_administrator')
            is_admin = self.env.user._is_admin()
            if not is_ods_administrator and not is_admin:
                raise ValidationError(_("You do not have permission to edit. Only as admin or ODS Administrator"))

    def create_extension(self, extensions):
        create_vals = []
        for extension in extensions:
            extension_exists = self.search([('ods_id', '=', extension.get('id'))])
            if not extension_exists:
                create_vals.append({
                    'ods_id': extension.get('id'),
                    'ods_data': extension.get('data'),
                })
            else:
                extension_exists.update({'ods_data': extension.get('data')})
        self.create(create_vals)
        for val in create_vals:
            val['ods_data'] = '*********'
        self.env['biz.ods.call.logs'].create({
            'ods_call_log_type': 'extension',
            'ods_message': str(create_vals),
            'ods_sync_status': 'sync_successful',
            'number_of_extension': int(len(create_vals))
        })

    def _update_res_user_settings(self, ods_user_id=False, voip_username=False, voip_secret=False):
        if not ods_user_id:
            return
        res_users_settings_record = self.env['res.users.settings']._find_or_create_for_user(ods_user_id)
        res_users_settings_record.update({
            'voip_username': voip_username,
            'voip_secret': voip_secret
        })
        ods_user_id.partner_id.update({'ods_number_extension': voip_username})

    def write(self, vals):
        if vals.get('ods_user_id') or vals.get('ods_user_id') is False:
            if vals.get('ods_user_id') is False:
                ods_user_id = self.ods_user_id
                self._update_res_user_settings(ods_user_id, False, False)
            else:
                if self.ods_user_id:
                    old_ods_user_id = self.ods_user_id
                    self._update_res_user_settings(old_ods_user_id, False, False)
                ods_user_id = self.env['res.users'].browse(vals.get('ods_user_id'))
                self._update_res_user_settings(ods_user_id, self.ods_id, self.ods_data)
        res = super().write(vals)
        return res

    def action_get_extension(self):
        _logger.info("GET EXTENSION")
        try:
            ods_service_name = self.env['ir.config_parameter'].sudo().get_param('biz_ods.ods_service_name')
            ods_auth_user = self.env['ir.config_parameter'].sudo().get_param('biz_ods.ods_auth_user')
            ods_auth_key = self.env['ir.config_parameter'].sudo().get_param('biz_ods.ods_auth_key')

            if not ods_service_name or not ods_auth_user or not ods_auth_key:
                string_ods_service_name = self.env['ir.model.fields'].with_context(lang=self.env.user.lang).get_field_string(
                    'res.config.settings')['ods_service_name']
                string_ods_auth_user = self.env['ir.model.fields'].with_context(lang=self.env.user.lang).get_field_string(
                    'res.config.settings')['ods_auth_user']
                string_ods_auth_key = self.env['ir.model.fields'].with_context(lang=self.env.user.lang).get_field_string(
                    'res.config.settings')['ods_auth_key']
                raise UserError(_("Fields '%s', '%s', '%s' cannot be empty(Go to Call Center ODS/Configuration/Settings)", string_ods_service_name, string_ods_auth_user, string_ods_auth_key))

            ods = ODS()
            ods.request_data.update({
                "ServiceCode": str(ods_service_name),
                "AuthUser": str(ods_auth_user),
                "AuthKey": str(ods_auth_key),
            })
            ods.response_data = ods.get_list_extension()
            if ods.response_data and ods.response_data.status_code == 200:
                body = json.loads(ods.response_data.text)
                if body and isinstance(body, dict) and body.get('result') == 'success' and body.get('data') not in [False, None]:
                    data = body.get('data')
                    self.create_extension(data)
                else:
                    pass
            else:
                self.env['biz.ods.call.logs'].create({
                    'ods_call_log_type': 'extension',
                    'ods_message': str(ods.response_data.text),
                    'ods_sync_status': 'sync_failed'
                })
        except Exception as error:
            self.env['biz.ods.call.logs'].create({
                'ods_call_log_type': 'extension',
                'ods_message': str(error),
                'ods_sync_status': 'sync_failed'
            })