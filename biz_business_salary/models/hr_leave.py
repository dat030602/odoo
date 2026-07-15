# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    is_warning_hr_leave_message = fields.Boolean(
        string='Hiển thị cảnh báo quá giờ',
        compute='_compute_is_warning_hr_leave_message'
    )

    @api.depends('employee_id', 'state', 'request_date_from', 'request_date_to', 'number_of_hours_display')
    def _compute_is_warning_hr_leave_message(self):
        for leave in self:
            leave.is_warning_hr_leave_message = False
            
            # The compute method should handle unsaved records gracefully.
            # Only proceed if the record has an employee and is not a draft state.
            if not leave.employee_id or not leave.request_date_from or leave.state not in ['validate', 'confirm']:
                continue

            # Calculate start and end of the month
            start_of_month = leave.request_date_from.replace(day=1)
            end_of_month = (start_of_month + relativedelta(months=1, days=-1))

            # Base domain for searching other approved leaves of the employee
            domain = [
                ('employee_id', '=', leave.employee_id.id),
                ('state', 'in', ['validate', 'confirm']),
                ('request_date_from', '>=', start_of_month),
                ('request_date_to', '<=', end_of_month),
            ]
            
            # If the record is NOT a new record (i.e., it's already saved),
            # add the condition to exclude itself from the search.
            # `self._origin.id` safely gives the real ID if it exists.
            if leave._origin.id:
                domain.append(('id', '!=', leave._origin.id))
            
            approved_leaves = self.search(domain)
            total_hours = sum(l.number_of_hours_display for l in approved_leaves)
            
            # Add hours of the current leave
            total_hours += leave.number_of_hours_display
            
            if total_hours > 8:
                leave.is_warning_hr_leave_message = True
