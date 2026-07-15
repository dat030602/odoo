import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, time

_logger = logging.getLogger(__name__)


class AttendanceWizard(models.TransientModel):
    _inherit = "attendance.wizard"

    def cron_sync_attendance(self):
        device_ids = self.env["attendance.device"].search([
            ("active", "=", True),
            ('state', '=', 'confirmed')
        ])
        not_state = device_ids.filtered(lambda x: x.is_not_create_attendance_data_by_state)
        self.with_context(synch_ignore_constraints=True).custom_sync_attendance(not_state)
        self.with_context(synch_ignore_constraints=True).sync_attendance_from_device(device_ids - not_state)

    def custom_sync_attendance(self, device_ids):
        """
        This method will synchronize all downloaded attendance data with Odoo attendance data.
        It do not download attendance data from the devices.
        """
        if not device_ids:
            return
        
        if self.fix_attendance_valid_before_synch:
            self.action_fix_user_attendance_valid()

        synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)

        error_msg = {}
        HrAttendance = self.env['hr.attendance'].sudo()
        DeviceUserAttendance = self.env['user.attendance']

        unsync_data = DeviceUserAttendance.search([
            ('hr_attendance_id', '=', False),
            ('user_id', '!=', False),
            ('device_id', 'in', device_ids.ids),
        ], order='timestamp ASC')

        for att in unsync_data:
            employee_id = att.user_id.employee_id
            if not employee_id:
                continue

            timestamp_date = (att.timestamp + timedelta(hours=7)).date()
            timestamp_from = datetime.combine(timestamp_date, time.min) - timedelta(hours=7)
            timestamp_to = datetime.combine(timestamp_date, time.max) - timedelta(hours=7)
            hr_attendance_id = HrAttendance.search([
                ("employee_id", "=", employee_id.id),
                ("check_out", "=", False),
                ('check_in','>=', timestamp_from),
                ('check_in','<=', timestamp_to),
                "|",
                ("checkin_device_id", "=", att.device_id.id),
                ("checkout_device_id", "=", att.device_id.id),
            ], limit=1)

            if hr_attendance_id:
                try:
                    hr_attendance_id.write({
                        "check_out": att.timestamp,
                        "checkout_device_id": att.device_id.id,
                        "activity_id": att.activity_id.id,
                        "is_write_by_cron": True
                    })
                except Exception as e:
                    if att.device_id not in error_msg:
                        error_msg[att.device_id] = ""

                    msg = ""
                    att_check_time = fields.Datetime.context_timestamp(att, fields.Datetime.from_string(att.timestamp))
                    msg += str(e) + "<br />"
                    msg += _("'Check Out' time cannot be earlier than 'Check In' time. Debug information:<br />"
                                    "* Employee: <strong>%s</strong><br />"
                                    "* Type: %s<br />"
                                    "* Attendance Check Time: %s<br />") % (employee_id.name, att.type, fields.Datetime.to_string(att_check_time))
                    _logger.error(msg)
                    error_msg[att.device_id] += msg
            else:
                hr_attendance_id = HrAttendance.search([
                    ('employee_id', '=', employee_id.id),
                    ('check_in', '=', att.timestamp),
                    ('checkin_device_id', '=', att.device_id.id)
                ], limit=1)

                if not hr_attendance_id:
                    try:
                        hr_attendance_id = HrAttendance.create({
                            'employee_id': employee_id.id,
                            'check_in': att.timestamp,
                            'checkin_device_id': att.device_id.id,
                            "activity_id": att.activity_id.id,
                            "check_out": False,
                            "checkout_device_id": False,
                            "is_create_by_cron": True,
                        })
                    except Exception as e:
                        _logger.error(e)

            if hr_attendance_id:
                att.write({'hr_attendance_id': hr_attendance_id.id})

        if error_msg:
            for device,error in error_msg.items():

                if not device.debug_message:
                    continue
                device.message_post(body=error)

    def sync_attendance_from_device(self, device_ids):
        """
        This method will synchronize all downloaded attendance data with Odoo attendance data.
        It do not download attendance data from the devices.
        """
        if not device_ids:
            return
        
        if self.fix_attendance_valid_before_synch:
            self.action_fix_user_attendance_valid()

        synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)

        error_msg = {}
        HrAttendance = self.env['hr.attendance'].with_context(synch_ignore_constraints=synch_ignore_constraints)

        activity_ids = self.env['attendance.activity'].search([])

        DeviceUserAttendance = self.env['user.attendance']

        for activity_id in activity_ids:
            unsync_data = DeviceUserAttendance.search([
                ('hr_attendance_id', '=', False),
                ('valid', '=', True),
                ('employee_id', '!=', False),
                ('device_id', 'in', device_ids.ids),
                ('activity_id', '=', activity_id.id)], 
            order='timestamp ASC')

            for att in unsync_data:
                employee_id = att.user_id.employee_id
                if not employee_id:
                    continue

                if att.type == 'checkout':
                    # find last attendance
                    hr_attendance_id = HrAttendance.search([
                        ('employee_id', '=', employee_id.id),
                        ('activity_id', 'in', (activity_id.id, False)),
                        ('check_in', '<=', att.timestamp)
                    ], limit=1, order='check_in DESC')

                    if hr_attendance_id:
                        try:
                            hr_attendance_id.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                'check_out': att.timestamp,
                                'checkout_device_id': att.device_id.id
                            })
                        except ValidationError as e:
                            if att.device_id not in error_msg:
                                error_msg[att.device_id] = ""

                            msg = ""
                            att_check_time = fields.Datetime.context_timestamp(att, fields.Datetime.from_string(att.timestamp))
                            msg += str(e) + "<br />"
                            msg += _("'Check Out' time cannot be earlier than 'Check In' time. Debug information:<br />"
                                          "* Employee: <strong>%s</strong><br />"
                                          "* Type: %s<br />"
                                          "* Attendance Check Time: %s<br />") % (employee_id.name, att.type, fields.Datetime.to_string(att_check_time))
                            _logger.error(msg)
                            error_msg[att.device_id] += msg
                else:
                    # create hr attendance data
                    hr_attendance_id = HrAttendance.search([
                        ('employee_id', '=', employee_id.id),
                        ('check_in', '=', att.timestamp),
                        ('checkin_device_id', '=', att.device_id.id),
                        ('activity_id', '=', activity_id.id)
                    ], limit=1)

                    if not hr_attendance_id:
                        try:
                            hr_attendance_id = HrAttendance.create({
                                'employee_id': employee_id.id,
                                'check_in': att.timestamp,
                                'checkin_device_id': att.device_id.id,
                                'activity_id': activity_id.id,
                            })
                        except Exception as e:
                            _logger.error(e)

                if hr_attendance_id:
                    att.write({
                        'hr_attendance_id': hr_attendance_id.id
                    })

        if error_msg:
            for device,error in error_msg.items():

                if not device.debug_message:
                    continue
                device.message_post(body=error)
