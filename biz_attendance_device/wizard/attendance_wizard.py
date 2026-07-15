import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class AttendanceWizard(models.TransientModel):
    _name = 'attendance.wizard'
    _description = 'Attendance Wizard'

    @api.model
    def _get_all_device_ids(self):
        all_devices = self.env['attendance.device'].search([('state', '=', 'confirmed')])
        if all_devices:
            return all_devices.ids
        else:
            return []

    device_ids = fields.Many2many('attendance.device', string='Devices', default=_get_all_device_ids, domain=[('state', '=', 'confirmed')])
    fix_attendance_valid_before_synch = fields.Boolean(string='Fix Attendance Valid', help="If checked, Odoo will recompute all attendance data for their valid"
                                                     " before synchronizing with HR Attendance (upon you hit the 'Synchronize Attendance' button)")

    def download_attendance_manually(self):
        if not self.device_ids:
            raise UserError(_('You must select at least one device to continue!'))
        self.device_ids.action_attendance_download()

    def download_device_attendance(self):
        devices = self.env['attendance.device'].search([('state', '=', 'confirmed')])
        devices.action_attendance_download()

    def cron_sync_attendance(self):
        self.with_context(synch_ignore_constraints=True).sync_attendance()

    def sync_attendance(self):
        """
        This method will synchronize all downloaded attendance data with Odoo attendance data.
        It do not download attendance data from the devices.
        """
        if self.fix_attendance_valid_before_synch:
            self.action_fix_user_attendance_valid()

        synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)

        error_msg = {}
        HrAttendance = self.env['hr.attendance'].with_context(synch_ignore_constraints=synch_ignore_constraints)

        activity_ids = self.env['attendance.activity'].search([])

        DeviceUserAttendance = self.env['user.attendance']

        last_employee_attendance = {}
        for activity_id in activity_ids:
            if activity_id.id not in last_employee_attendance.keys():
                last_employee_attendance[activity_id.id] = {}

            unsync_data = DeviceUserAttendance.search([('hr_attendance_id', '=', False),
                                                       ('valid', '=', True),
                                                       ('employee_id', '!=', False),
                                                       ], order='timestamp ASC')
            for att in unsync_data:
                employee_id = att.user_id.employee_id
                if employee_id.id not in last_employee_attendance[activity_id.id].keys():
                    last_employee_attendance[activity_id.id][employee_id.id] = False

                if att.type == 'checkout':
                    # find last attendance
                    last_employee_attendance[activity_id.id][employee_id.id] = HrAttendance.search(
                        [('employee_id', '=', employee_id.id),
                         ('activity_id', 'in', (activity_id.id, False)),
                         ('check_in', '<=', att.timestamp)], limit=1, order='check_in DESC')

                    hr_attendance_id = last_employee_attendance[activity_id.id][employee_id.id]

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
                    vals = {
                        'employee_id': employee_id.id,
                        'check_in': att.timestamp,
                        'checkin_device_id': att.device_id.id,
                        'activity_id': activity_id.id,
                        }
                    hr_attendance_id = HrAttendance.search([
                        ('employee_id', '=', employee_id.id),
                        ('check_in', '=', att.timestamp),
                        ('checkin_device_id', '=', att.device_id.id),
                        ('activity_id', '=', activity_id.id)], limit=1)
                    if not hr_attendance_id:
                        try:
                            hr_attendance_id = HrAttendance.create(vals)
                        except Exception as e:
                            _logger.error(e)

                if hr_attendance_id:
                    att.write({
                        'hr_attendance_id': hr_attendance_id.id
                        })

        # Tìm các bản ghi user.attendance đơn lẻ, valid=False, chưa sync
        unsync_invalid = DeviceUserAttendance.search([
            ('hr_attendance_id', '=', False),
            ('valid', '=', False),
            ('employee_id', '!=', False),
        ], order='timestamp ASC')

        for att in unsync_invalid:
            print('Có dữ liệu không')
            print(att)
            employee = att.user_id.employee_id
            is_sanxuat = employee.department_id and employee.department_id.parent_id and employee.department_id.parent_id.name == 'Sản xuất'
            if not employee or not employee.resource_calendar_id:
                continue

            # Cộng thêm 7 giờ để chuyển sang giờ Việt Nam
            dt = fields.Datetime.from_string(att.timestamp) + timedelta(hours=7)
            day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            if is_sanxuat:
                day_end = day_start + timedelta(hours=22)
            else:
                day_end = day_start + timedelta(days=1)
            print('day_start', day_start)
            print('day_end', day_end)
            same_day_count = DeviceUserAttendance.search_count([
                ('employee_id', '=', employee.id),
                ('timestamp', '>=', day_start),
                ('timestamp', '<', day_end),
            ])
            print('same_day_count', same_day_count)
            if same_day_count > 1:
                continue

            # Xác định thứ trong tuần và giờ
            dayofweek = str(dt.weekday())  # Odoo: 0=Monday, 6=Sunday
            print('dayofweek', dayofweek)
            print('dt.hour', dt.hour)
            print('dt.minute', dt.minute)
            print('dt.second', dt.second)
            print('dt', dt)
            hour = float('%02d.%02d' % (dt.hour, dt.minute))
            print('hour', hour)

            # Trường hợp đặc biệt cho phòng Sản xuất
            
            if is_sanxuat:
                # Nếu timestamp từ 4:00 đến 7:00
                if (dt.hour > 4 or (dt.hour == 4 and dt.minute >= 0)) and (dt.hour < 7 or (dt.hour == 7 and dt.minute == 0)):
                    vals = {
                        'employee_id': employee.id,
                        'activity_id': att.activity_id.id if hasattr(att, 'activity_id') else False,
                        'checkin_device_id': att.device_id.id,
                        'checkout_device_id': att.device_id.id,
                        'check_error': True,
                        'check_in': att.timestamp,
                        'check_out': fields.Datetime.to_string(dt.replace(hour=18, minute=0, second=0, microsecond=0) - timedelta(hours=7)),
                    }
                    try:
                        hr_attendance = HrAttendance.create(vals)
                        att.write({'hr_attendance_id': hr_attendance.id})
                    except Exception as e:
                        _logger.error(e)
                    continue
                # Nếu timestamp từ 16:00 đến 20:00
                if (dt.hour > 16 or (dt.hour == 16 and dt.minute >= 0)) and (dt.hour < 20 or (dt.hour == 20 and dt.minute == 0)):
                    vals = {
                        'employee_id': employee.id,
                        'activity_id': att.activity_id.id if hasattr(att, 'activity_id') else False,
                        'checkin_device_id': att.device_id.id,
                        'checkout_device_id': att.device_id.id,
                        'check_error': True,
                        'check_out': att.timestamp,
                        'check_in': fields.Datetime.to_string(dt.replace(hour=6, minute=0, second=0, microsecond=0) - timedelta(hours=7)),
                    }
                    print('vals', vals)
                    try:
                        hr_attendance = HrAttendance.create(vals)
                        att.write({'hr_attendance_id': hr_attendance.id})
                    except Exception as e:
                        _logger.error(e)
                    continue

            # --- Giữ nguyên các chức năng cũ cho các trường hợp khác ---
            # Tìm dòng lịch làm việc phù hợp
            matched_line = None
            for line in employee.resource_calendar_id.attendance_ids:
                print('line', line)
                print('line.dayofweek', line.dayofweek)
                print('line.hour_from', line.hour_from)
                print('line.hour_to', line.hour_to)
                if line.dayofweek == dayofweek and (line.hour_from - 2) <= hour < (line.hour_to - 2) and line.day_period == 'morning':
                    matched_line = line
                    break
                elif line.dayofweek == dayofweek and line.hour_from <= hour < (line.hour_to + 3) and line.day_period == 'afternoon':
                    matched_line = line
                    break
            print('matched_line', matched_line)
            if not matched_line:
                continue

            # Mở rộng: tìm dòng morning/afternoon cùng ngày
            morning_line = None
            afternoon_line = None
            for line in employee.resource_calendar_id.attendance_ids:
                if line.dayofweek == dayofweek:
                    if line.day_period == 'morning':
                        morning_line = line
                    elif line.day_period == 'afternoon':
                        afternoon_line = line

            vals = {
                'employee_id': employee.id,
                'activity_id': att.activity_id.id if hasattr(att, 'activity_id') else False,
                'checkin_device_id': att.device_id.id,
                'checkout_device_id': att.device_id.id,
                'check_error': True,
            }
            if matched_line.day_period == 'morning':
                vals['check_in'] = att.timestamp
                # Nếu có dòng afternoon, set check_out = hour_to của afternoon
                if afternoon_line:
                    out_dt = dt.replace(hour=int(afternoon_line.hour_to), minute=int((afternoon_line.hour_to % 1) * 60), second=0, microsecond=0)
                    vals['check_out'] = fields.Datetime.to_string(out_dt - timedelta(hours=7))
            elif matched_line.day_period == 'afternoon':
                vals['check_out'] = att.timestamp
                # Nếu có dòng morning, set check_in = hour_from của morning
                if morning_line:
                    in_dt = dt.replace(hour=int(morning_line.hour_from), minute=int((morning_line.hour_from % 1) * 60), second=0, microsecond=0)
                    vals['check_in'] = fields.Datetime.to_string(in_dt - timedelta(hours=7))

            try:
                hr_attendance = HrAttendance.create(vals)
                att.write({'hr_attendance_id': hr_attendance.id})
            except Exception as e:
                _logger.error(e)

        if bool(error_msg):
            for device in error_msg.keys():

                if not device.debug_message:
                    continue
                device.message_post(body=error_msg[device])

    def clear_attendance(self):
        if not self.device_ids:
            raise (_('You must select at least one device to continue!'))
        if not self.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            raise UserError(_('Only HR Attendance Managers can manually clear device attendance data'))

        for device in self.device_ids:
                device.clearAttendance()

    def action_fix_user_attendance_valid(self):
        all_attendances = self.env['user.attendance'].search([])
        for attendance in all_attendances:
            if attendance.is_valid():
                attendance.write({'valid': True})
            else:
                attendance.write({'valid': False})
