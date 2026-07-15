# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import urllib.request

from odoo import fields, models, _
from datetime import datetime
from .ods_component import STATUS_WEBHOOK_VI, DIRECTION_WEBHOOK_VI
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

class ResPartner(models.Model):
    _inherit = 'res.partner'

    ods_number_extension = fields.Char(string="Number Extension(ODS)")
    # Computed (for stat button)
    ods_history_call_count = fields.Integer(compute="_compute_ods_history_call")

    def _compute_ods_history_call(self):
        for record in self:
            calls = self.env['biz.ods.call.history'].search(['|', ('caller_partner_id', '=', self.id), ('receive_partner_id', '=', self.id)])
            record.ods_history_call_count = len(calls)

    def action_view_ods_call_history(self):
        res = self.sudo().env.ref("biz_ods.biz_ods_call_history_partner_action").sudo().read()[0]
        res['domain'] = ['|', ('caller_partner_id', '=', self.id), ('receive_partner_id', '=', self.id)]
        return res

    def create_activity_history_call(self):
        attachment = False
        datas = self._context.get('datas', False)
        extension = self._context.get('extension', False)
        if datas and extension:
            partner = self.search(['|', ('phone', '=', datas['ReceiptNumber']), ('mobile', '=', datas['ReceiptNumber'])], limit=1)
            if partner:
                data = datas.get('Data')
                key = datas.get('Key', '')
                status = datas.get('Status', '')
                direction = datas.get('Direction', '')
                number_pbx = datas.get('NumberPBX', '')
                caller_number = datas.get('CallNumber')
                receipt_number = datas.get('ReceiptNumber')
                real_time_call = data.get('RealTimeCall') if data else '0'
                date_start = datetime.strptime(datas['DateStart'], DEFAULT_SERVER_DATETIME_FORMAT)

                if extension.ods_user_id.lang == 'vi_VN':
                    status = STATUS_WEBHOOK_VI.get(status)
                    direction = DIRECTION_WEBHOOK_VI.get(direction)
                    note = _('''
                        Mã cuộc gọi: %(key)s<br/>
                        Trạng thái: %(status)s - Hướng: %(direction)s<br/>
                        Thời điểm cuộc gọi: %(date_start)s<br/>
                        Thời gian đàm thoại: %(real_time_call)s<br/>
                        Số người gọi: %(caller_number)s(%(number_pbx)s)<br/>
                        Số người nhận: %(receipt_number)s<br/>
                    ''', key=key,
                             status=status,
                             direction=direction,
                             date_start=str(date_start),
                             real_time_call=real_time_call,
                             caller_number=caller_number,
                             number_pbx=number_pbx,
                             receipt_number=receipt_number)
                    direction = DIRECTION_WEBHOOK_VI.get(datas['Direction'], '')
                else:
                    note = _('''
                        Key: %(key)s<br/>
                        Status: %(status)s - Direction: %(direction)s<br/>
                        Date Start: %(date_start)s<br/>
                        Real Time Call: %(real_time_call)s<br/>
                        Caller Number: %(caller_number)s(%(number_pbx)s)<br/>
                        Receipt Number: %(receipt_number)s<br/>
                    ''', key=key,
                             status=status,
                             direction=direction,
                             date_start=str(date_start),
                             real_time_call=real_time_call,
                             caller_number=caller_number,
                             number_pbx=number_pbx,
                             receipt_number=receipt_number)

                activity_type_id = self.env.ref('mail.mail_activity_data_call').id if self.env.ref(
                    'mail.mail_activity_data_call') else False
                summary = f"{datas['Key']} - {direction} - {status} - {str(date_start.date())}"
                activity = partner.activity_schedule(
                    activity_type_id=activity_type_id,
                    summary=summary,
                    note=note,
                    user_id=extension.ods_user_id.id,
                    date_deadline=date_start.date(),
                )
                if data:
                    html_file = urllib.request.urlopen(data.get('LinkFile'))
                    if html_file.status == 200:
                        attachment = self.env['ir.attachment'].sudo().create({
                            'name': key + '.mp3',
                            'datas': base64.b64encode(html_file.read()),
                            'mimetype': 'audio/mpeg',
                            'res_id': partner.id,
                            'res_model': 'res.partner',
                        })
                if attachment:
                    mail_message = activity._action_done(feedback=None, attachment_ids=[attachment.id])
                else:
                    mail_message = activity._action_done(feedback=None, attachment_ids=None)
                # Check unlink mail.message
                call_history = self.env['biz.ods.call.history'].sudo().search([('ods_key', '=', key)], limit=1)
                if call_history:
                    if call_history.mail_message_id:
                        call_history.mail_message_id.unlink()
                        call_history.update({'mail_message_id': mail_message[0].id})
                    else:
                        call_history.update({'mail_message_id': mail_message[0].id})
                self.env['biz.ods.call.logs'].create({
                    'ods_call_log_type': 'outbound',
                    'ods_message': datas,
                    'ods_status': datas.get('Status').lower() if datas.get('Status') else False,
                    'ods_direction': 'outbound'
                })
