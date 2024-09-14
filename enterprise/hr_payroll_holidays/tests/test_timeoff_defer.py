# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.fields import Datetime
from odoo.tests.common import tagged
from odoo.addons.hr_payroll_holidays.tests.common import TestPayrollHolidaysBase

from dateutil.relativedelta import relativedelta

@tagged('payroll_holidays_defer')
class TestTimeoffDefer(TestPayrollHolidaysBase):

    def test_no_defer(self):
        #create payslip -> waiting or draft
        payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip',
            'employee_id': self.emp.id,
        })

        # Puts the payslip to draft/waiting
        payslip.compute_sheet()

        #create a time off for our employee, validating it now should not put it as to_defer
        leave = self.env['hr.leave'].create({
            'name': 'Golf time',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': (Datetime.today() + relativedelta(day=13)),
            'date_to': (Datetime.today() + relativedelta(day=16)),
            'number_of_days': 3,
        })
        leave.action_approve()

        self.assertNotEqual(leave.payslip_state, 'blocked', 'Leave should not be to defer')

    def test_to_defer(self):
        #create payslip
        payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip',
            'employee_id': self.emp.id,
        })

        # Puts the payslip to draft/waiting
        payslip.compute_sheet()
        payslip.action_payslip_done()

        #create a time off for our employee, validating it now should put it as to_defer
        leave = self.env['hr.leave'].create({
            'name': 'Golf time',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': (Datetime.today() + relativedelta(day=13)),
            'date_to': (Datetime.today() + relativedelta(day=16)),
            'number_of_days': 3,
        })
        leave.action_approve()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

    def test_multi_payslip_defer(self):
        #A leave should only be set to defer if ALL colliding with the time period of the time off are in a done state
        # it should not happen if a payslip for that time period is still in a waiting state

        #create payslip -> waiting
        waiting_payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip draft',
            'employee_id': self.emp.id,
        })
        #payslip -> done
        done_payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip done',
            'employee_id': self.emp.id,
        })

        # Puts the waiting payslip to draft/waiting
        waiting_payslip.compute_sheet()
        # Puts the done payslip to the done state
        done_payslip.compute_sheet()
        done_payslip.action_payslip_done()

        #create a time off for our employee, validating it now should not put it as to_defer
        leave = self.env['hr.leave'].create({
            'name': 'Golf time',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': (Datetime.today() + relativedelta(day=13)),
            'date_to': (Datetime.today() + relativedelta(day=16)),
            'number_of_days': 3,
        })
        leave.action_approve()

        self.assertNotEqual(leave.payslip_state, 'blocked', 'Leave should not be to defer')

    def test_payslip_paid_past(self):
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })

        payslip.compute_sheet()
        self.assertEqual(payslip.state, 'verify')

        self.env['hr.leave'].with_user(self.vlad).create({
            'name': 'Tennis',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': '2022-01-12',
            'date_to': '2022-01-12',
            'number_of_days': 1,
        })
        payslip.action_payslip_done()

        # A Simple User can't request a leave if a payslip is paid
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.vlad).create({
                'name': 'Tennis',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.emp.id,
                'date_from': '2022-01-19',
                'date_to': '2022-01-19',
                'number_of_days': 1,
            })

        # Check overlapping periods with no payslip
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.vlad).create({
                'name': 'Tennis',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.emp.id,
                'date_from': '2022-01-31',
                'date_to': '2022-02-01',
                'number_of_days': 2,
            })

        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.vlad).create({
                'name': 'Tennis',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.emp.id,
                'date_from': '2021-01-31',
                'date_to': '2022-01-03',
                'number_of_days': 2,
            })

        # But a time off officer can
        self.env['hr.leave'].with_user(self.joseph).create({
            'name': 'Tennis',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': '2022-01-19',
            'date_to': '2022-01-19',
            'number_of_days': 1,
        })
