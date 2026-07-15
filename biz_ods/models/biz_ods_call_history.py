# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import base64
import logging
import requests
import threading

from datetime import datetime, timedelta
from .ods_component import ODS, ODS_PAGE_SIZE, DEFAULT_ODS_DATETIME_FORMAT
from odoo import fields, models, api
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class CallHistory(models.Model):
    _name = 'biz.ods.call.history'
    _description = 'Call History'
    _rec_name = 'ods_key'

    # Data Fields API
    ods_key = fields.Char(string="Key")
    ods_call_date = fields.Datetime(string="Call Date")
    ods_call_only_date = fields.Date(string="Call Date(Only Date)")
    ods_caller_number = fields.Char(string="Caller Number")
    ods_caller_name = fields.Char(string="Caller Name(ODS)")
    ods_head_number = fields.Char(string="Head Number")
    ods_receive_number = fields.Char(string="Receive Number")
    ods_receive_group = fields.Char(string="Receive Group")
    ods_status = fields.Selection(selection=[
        ('answered', "Answer"),
        ('no_answer', "No Answer"),
        ('busy', "Busy"),
        ('failed', "Failed"),
        ('cancel', "Cancel"),
        ('answered_elsewhere', 'Answered Elsewhere')
    ], string="Status")
    ods_total_call_time = fields.Integer(string="Total Call Time")
    ods_real_call_time = fields.Integer(string="Real Call Time")
    ods_link_file = fields.Char(string="Link File")
    ods_type_call = fields.Selection(selection=[
        ('inbound', "Inbound"),
        ('outbound', "Outbound"),
        ('local', "Local")
    ], string="Type Call")

    #
    caller_name = fields.Char(string="Caller Name", compute="_compute_caller", store=True)
    receive_name = fields.Char(string="Receive Name", compute="_compute_receive", store=True)
    call_content = fields.Text(string="Call Content")
    recording_data = fields.Binary(related='recording_file_id.datas', string="Recording")
    recording_name = fields.Char(related='recording_file_id.name')

    # Relational
    caller_partner_id = fields.Many2one(comodel_name="res.partner", string="Caller Partner ID", compute="_compute_caller", store=True)
    caller_user_id = fields.Many2one(comodel_name="res.users", string="Caller User ID", compute="_compute_caller", store=True)
    receive_partner_id = fields.Many2one(comodel_name="res.partner", string="Receive Partner ID", compute="_compute_receive", store=True)
    receive_user_id = fields.Many2one(comodel_name="res.users", string="Receive User ID", compute="_compute_receive", store=True)
    mail_message_id = fields.Many2one(comodel_name='mail.message')
    recording_file_id = fields.Many2one('ir.attachment', string='Recording File')

    # --- Compute Methods ---

    @api.depends('ods_caller_number', 'ods_type_call')
    def _compute_caller(self):
        for record in self:
            partner = partner_id = self.env['res.partner']
            dict_numbers = partner.search([('phone', '!=', False), ('mobile', '!=', False)]).phone_get_sanitized_numbers()
            for key, value in dict_numbers.items():
                if isinstance(value, str) and record.ods_caller_number == value.strip('+'):
                    partner_id = partner.browse(key)
                    break

            if not partner_id:
                caller_number = record.ods_caller_number
                if caller_number:
                    partner_id = partner.search(['|', '|', ('phone', '=', caller_number), ('mobile', '=', caller_number), ('ods_number_extension', '=', caller_number)], limit=1)

            record.caller_name = partner_id.name if partner_id else record.ods_caller_name
            record.caller_partner_id = partner_id.id if partner_id else False
            record.caller_user_id = partner_id.user_id.id if partner_id else False

    @api.depends('ods_receive_number', 'ods_type_call')
    def _compute_receive(self):
        for record in self:
            partner = partner_id = self.env['res.partner']
            dict_numbers = partner.search([('phone', '!=', False), ('mobile', '!=', False)]).phone_get_sanitized_numbers()
            for key, value in dict_numbers.items():
                if isinstance(value, str) and record.ods_receive_number == value.strip('+'):
                    partner_id = partner.browse(key)
                    break

            if not partner_id:
                caller_number = record.ods_receive_number
                if caller_number:
                    partner_id = partner.search(['|', '|', ('phone', '=', caller_number), ('mobile', '=', caller_number), ('ods_number_extension', '=', caller_number)], limit=1)

            record.receive_name = partner_id.name if partner_id else record.ods_receive_number
            record.receive_partner_id = partner_id.id if partner_id else False
            record.receive_user_id = partner_id.user_id.id if partner_id else False

    # --- Action Methods ---

    def create_call_history(self, calls):
        self = self.sudo()
        create_vals = []
        for call in calls:
            if call.get("event") == "hide":
                continue
            call_exists = self.search([('ods_key', '=', call.get('linkedId'))])
            if call.get('timeCall'):
                callDate = datetime.strptime(call.get('timeCall'), DEFAULT_ODS_DATETIME_FORMAT) - timedelta(hours=7)
            else:
                callDate = False
            status = call.get('disposition').lower().replace(' ', '_') if call.get('disposition') else False
            if status and status == 'cancel':
                status = 'no_answer'
            elif status and status == 'answered_elsewhere':
                status = 'answered'
            typecall = call.get('direction').lower() if call.get('direction') else False
            if call.get('duration'):
                total_call_time = int(call.get('duration'))
            else:
                total_call_time = 0
            if call.get('billsecAgent'):
                real_call_time = int(call.get('billsecAgent'))
            else:
                real_call_time = 0
            if not call_exists:
                create_vals.append({
                    'ods_key': call.get('linkedId'),
                    'ods_call_date': callDate,
                    'ods_call_only_date': callDate.date() if callDate else False,
                    'ods_caller_number': call.get('src'),
                    'ods_caller_name': call.get('srcName'),
                    'ods_head_number': call.get('did'),
                    'ods_receive_group': call.get('queue'),
                    'ods_receive_number': f"{call.get('dst')} - Gọi tiếp đến số> {call.get('transfered')}" if call.get('dst') and call.get('transfered') else call.get('dst'),
                    'ods_status': status,
                    'ods_total_call_time': total_call_time,
                    'ods_real_call_time': real_call_time,
                    'ods_link_file': call.get('recordingFile'),
                    'ods_type_call': typecall
                })
            else:
                call_exists.update({
                    'ods_call_date': callDate,
                    'ods_call_only_date': callDate.date() if callDate else False,
                    'ods_caller_number': call.get('src'),
                    'ods_caller_name': call.get('srcName'),
                    'ods_head_number': call.get('did'),
                    'ods_receive_group': call.get('queue'),
                    'ods_receive_number': f"{call.get('dst')} - Gọi tiếp đến số> {call.get('transfered')}" if call.get('dst') and call.get('transfered') else call.get('dst'),
                    'ods_status': status,
                    'ods_total_call_time': total_call_time,
                    'ods_real_call_time': real_call_time,
                    'ods_link_file': call.get('recordingFile'),
                    'ods_type_call': typecall
                })
        self.create(create_vals)
        self.env['biz.ods.call.logs'].create({
            'ods_call_log_type': 'call_history',
            'ods_message': str(create_vals),
            'ods_sync_status': 'sync_successful',
            'number_of_call_history': int(len(create_vals))
        })
        self._cr.commit()


    def create_update_call_history_webhook(self):
        create_vals = []
        datas = self._context.get('datas', False)
        extension = self._context.get('extension', False)
        if datas and extension:
            data = datas.get('Data') if datas.get('Data') is not None else {}
            call_exists = self.search([('ods_key', '=', datas.get('KeyRinging'))])
            if datas.get('DateStart'):
                callDate = datetime.strptime(datas.get('DateStart'), DEFAULT_SERVER_DATETIME_FORMAT) - timedelta(hours=7)
            else:
                callDate = False
            if datas.get('Status'):
                if datas.get('Status') == 'Down_Out':
                    status = 'answered'
                else:
                    status = 'no_answer'
            typecall = datas.get('Direction').lower() if datas.get('Direction') else False
            if data.get('TotalTimeCall'):
                total_time_call = int(data.get('TotalTimeCall'))
            else:
                total_time_call = 0
            if data.get('RealTimeCall'):
                real_time_call = int(data.get('RealTimeCall'))
            else:
                real_time_call = 0
            if not call_exists:
                create_vals.append({
                    'ods_key': datas.get('KeyRinging'),
                    'ods_call_date': callDate,
                    'ods_call_only_date': callDate.date() if callDate else False,
                    'ods_head_number': datas.get('NumberPBX'),
                    'ods_caller_number': datas.get('CallNumber'),
                    'ods_caller_name': datas.get('CallName'),
                    'ods_receive_group': datas.get('QueueNumber'),
                    'ods_receive_number': datas.get('ReceiptNumber'),
                    'ods_status': status,
                    'ods_total_call_time': total_time_call,
                    'ods_real_call_time': real_time_call,
                    'ods_link_file': data.get('LinkFile'),
                    'ods_type_call': typecall
                })
            else:
                ods = ODS()
                ods_service_name = self.env['ir.config_parameter'].sudo().get_param('biz_ods.ods_service_name')
                ods_auth_user = self.env['ir.config_parameter'].sudo().get_param('biz_ods.ods_auth_user')
                ods_auth_key = self.env['ir.config_parameter'].sudo().get_param('biz_ods.ods_auth_key')
                ods.request_data.update({
                    "ServiceName": str(ods_service_name),
                    "AuthUser": str(ods_auth_user),
                    "AuthKey": str(ods_auth_key),
                    "Key": str(call_exists.ods_key)
                })
                ods.response_data = ods.get_call_history_v2()
                if ods.response_data and ods.response_data.status_code == 200:
                    body = json.loads(ods.response_data.text)
                    if body and isinstance(body, dict) and body.get('result') == 'success' and body.get('data') not in [
                        False, None]:
                        data = body.get('data')
                        self.create_call_history(data)
        if not call_exists:
            self.create(create_vals)
            self.env['biz.ods.call.logs'].create({
                'ods_call_log_type': 'call_history',
                'ods_message': str(create_vals),
                'ods_sync_status': 'sync_successful',
                'number_of_call_history': int(len(create_vals))
            })

    def action_get_call_history(self, page_index=1, count_data=0):
        _logger.info("GET CALL HISTORY")
        try:
            ods_service_name = self.env['ir.config_parameter'].sudo().get_param('biz_ods.ods_service_name')
            ods_auth_user = self.env['ir.config_parameter'].sudo().get_param('biz_ods.ods_auth_user')
            ods_auth_key = self.env['ir.config_parameter'].sudo().get_param('biz_ods.ods_auth_key')
            ods_from_datetime = self._context.get('ods_from_datetime', False)
            ods_to_datetime = self._context.get('ods_to_datetime', False)
            ods_type_get = self._context.get('ods_type_get', False)

            if not ods_service_name or not ods_auth_user or not ods_auth_key:
                string_ods_service_name = self.env['ir.model.fields'].with_context(lang=self.env.user.lang).get_field_string(
                    'res.config.settings')['ods_service_name']
                string_ods_auth_user = self.env['ir.model.fields'].with_context(lang=self.env.user.lang).get_field_string(
                    'res.config.settings')['ods_auth_user']
                string_ods_auth_key = self.env['ir.model.fields'].with_context(lang=self.env.user.lang).get_field_string(
                    'res.config.settings')['ods_auth_key']
                raise UserError(_("Fields '%s', '%s', '%s' cannot be empty(Go to Call Center ODS/Configuration/Settings)", string_ods_service_name, string_ods_auth_user, string_ods_auth_key))

            ods = ODS()
            ods_page_size = ODS_PAGE_SIZE
            if ods_from_datetime:
                ods_from_datetime = ods_from_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                ods_from_datetime = datetime.combine(fields.Datetime.now(), datetime.min.time()).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if ods_to_datetime:
                ods_to_datetime = ods_to_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                ods_to_datetime = datetime.combine(fields.Datetime.today(), datetime.max.time()).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if not ods_type_get:
                ods_type_get = "0" #all

            ods.request_data.update({
                "ServiceName": str(ods_service_name),
                "AuthUser": str(ods_auth_user),
                "AuthKey": str(ods_auth_key),
                "TypeGet": int(ods_type_get),
                "DateStart": str(ods_from_datetime),
                "DateEnd": str(ods_to_datetime),
                "PageIndex": int(page_index),
                "PageSize": int(ods_page_size)
            })
            ods.response_data = ods.get_call_history_v2()
            if ods.response_data and ods.response_data.status_code == 200:
                body = json.loads(ods.response_data.text)
                if body and isinstance(body, dict) and body.get('result') == 'success' and body.get('data') not in [False, None]:
                    data = body.get('data')
                    total = int(body.get('total'))
                    count_data = count_data + len(data) if isinstance(data, list) else 0
                    self.create_call_history(data)
                    _logger.info(f"Total: {total}, Count Data: {count_data}")
                    if total and total > 1 and count_data < total:
                        self.action_get_call_history(page_index=page_index+1, count_data=count_data)
                else:
                    pass
            else:
                self.env['biz.ods.call.logs'].create({
                    'ods_call_log_type': 'call_history',
                    'ods_message': str(ods.response_data.text),
                    'ods_sync_status': 'sync_failed'
                })
        except Exception as error:
            self.env['biz.ods.call.logs'].create({
                'ods_call_log_type': 'call_history',
                'ods_message': str(error),
                'ods_sync_status': 'sync_failed'
            })

    def action_download_ods_link_file(self):
        if self.ods_link_file:
            html_file = requests.get(self.ods_link_file)
            if html_file.status_code != 200 or html_file.url != "https://90.cloudfone.vn/Home/Errors":
                message = _("Get the call recording file successfully!")
                attachment = self.env['ir.attachment'].create({
                    'name': self.ods_key + '.wav',
                    'datas': base64.b64encode(html_file.content),
                    'mimetype': 'audio/wav',
                    'res_id': self.id,
                    'res_model': 'biz.ods.call.history',
                })
                self.update({'recording_file_id': attachment.id})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload'
                    # 'tag': 'display_notification',
                    # 'params': {
                    #     'message': message,
                    #     'type': 'success',
                    #     'sticky': False,
                    # },
                    # 'next': {'type': 'ir.actions.act_window_close'}
                }
            else:
                raise UserError(_("Can't find the recording file, please contact ODS(CloudFone) for support"))

    # --- Cron Methods ---

    def _cron_get_call_history(self, page_index=1, count_data=0):
        _logger.info("CRON GET CALL HISTORY")
        try:
            ods_service_name = self.env['ir.config_parameter'].sudo().get_param('biz_ods.ods_service_name')
            ods_auth_user = self.env['ir.config_parameter'].sudo().get_param('biz_ods.ods_auth_user')
            ods_auth_key = self.env['ir.config_parameter'].sudo().get_param('biz_ods.ods_auth_key')
            ods_from_datetime = self._context.get('ods_from_datetime', False)
            ods_to_datetime = self._context.get('ods_to_datetime', False)
            ods_type_get = self._context.get('ods_type_get', False)

            if not ods_service_name or not ods_auth_user or not ods_auth_key:
                string_ods_service_name = self.env['ir.model.fields'].with_context(lang=self.env.user.lang).get_field_string(
                    'res.config.settings')['ods_service_name']
                string_ods_auth_user = self.env['ir.model.fields'].with_context(lang=self.env.user.lang).get_field_string(
                    'res.config.settings')['ods_auth_user']
                string_ods_auth_key = self.env['ir.model.fields'].with_context(lang=self.env.user.lang).get_field_string(
                    'res.config.settings')['ods_auth_key']
                error_msg = _("Fields '%s', '%s', '%s' cannot be empty(Go to Call Center ODS/Configuration/Settings)", string_ods_service_name, string_ods_auth_user, string_ods_auth_key)
                self.env['biz.ods.call.logs'].create({
                    'ods_call_log_type': 'call_history',
                    'ods_message': str(error_msg),
                    'ods_sync_status': 'sync_failed'
                })
                return

            ods = ODS()
            ods_page_size = ODS_PAGE_SIZE
            if ods_from_datetime:
                ods_from_datetime = ods_from_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                ods_from_datetime = datetime.combine(fields.Datetime.now(), datetime.min.time()).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if ods_to_datetime:
                ods_to_datetime = ods_to_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                ods_to_datetime = datetime.combine(fields.Datetime.today(), datetime.max.time()).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if not ods_type_get:
                ods_type_get = "0" #all

            ods.request_data.update({
                "ServiceName": str(ods_service_name),
                "AuthUser": str(ods_auth_user),
                "AuthKey": str(ods_auth_key),
                "TypeGet": int(ods_type_get),
                "DateStart": str(ods_from_datetime),
                "DateEnd": str(ods_to_datetime),
                "PageIndex": int(page_index),
                "PageSize": int(ods_page_size)
            })
            ods.response_data = ods.get_call_history_v2()
            if ods.response_data and ods.response_data.status_code == 200:
                body = json.loads(ods.response_data.text)
                if body and isinstance(body, dict) and body.get('result') == 'success' and body.get('data') not in [False, None]:
                    data = body.get('data')
                    total = int(body.get('total'))
                    count_data = count_data + len(data) if isinstance(data, list) else 0
                    self.create_call_history(data)
                    if total and total > 1 and count_data < total:
                        self.action_get_call_history(page_index=page_index+1, count_data=count_data)
                    else:
                        self._cr.commit()
                        self._cr.reset()
                        self.env['biz.ods.call.history'].action_run_cron_audio_call_history()
                else:
                    pass
            else:
                self.env['biz.ods.call.logs'].create({
                    'ods_call_log_type': 'call_history',
                    'ods_message': str(ods.response_data.text),
                    'ods_sync_status': 'sync_failed'
                })
        except Exception as error:
            self.env['biz.ods.call.logs'].create({
                'ods_call_log_type': 'call_history',
                'ods_message': str(error),
                'ods_sync_status': 'sync_failed'
            })

    def action_run_cron_audio_call_history(self):
        self._start_thread_audio_call_history()

    def _start_thread_audio_call_history(self):
        threaded_calculation = threading.Thread(target=self._thread_function_audio_call_history, args=())
        threaded_calculation.start()

    def _thread_function_audio_call_history(self):
        with self.pool.cursor() as new_cr:
            self = self.with_env(self.env(cr=new_cr))
            self._cron_get_audio_call_history()
            self._cr.close()

    def _cron_get_audio_call_history(self):
        _logger.info("CRON GET AUDIO CALL HISTORY")
        try:
            call_history = self.search([("ods_link_file", "not in", [False, '']), ("recording_file_id", "=", False)], order="id DESC")
            for call in call_history:
                html_file = requests.get(call.ods_link_file)
                if html_file.status_code != 200 or html_file.url != "https://90.cloudfone.vn/Home/Errors":
                    attachment = self.env['ir.attachment'].create({
                        'name': call.ods_key + '.wav',
                        'datas': base64.b64encode(html_file.content),
                        'mimetype': 'audio/wav',
                        'res_id': call.id,
                        'res_model': 'biz.ods.call.history',
                    })
                    call.update({'recording_file_id': attachment.id})
                    self.env.cr.commit()
            _logger.info("DONE CRON GET AUDIO CALL HISTORY")
        except Exception as error:
            self.env['biz.ods.call.logs'].create({
                'ods_call_log_type': 'call_history',
                'ods_message': str(error),
                'ods_sync_status': 'sync_failed'
            })