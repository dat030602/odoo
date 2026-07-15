from odoo.tests import tagged

from .common import HrTestEmployeeCommon


@tagged('post_install', '-at_install')
class TestPartner(HrTestEmployeeCommon):

    def test_compute_is_employee(self):
        self.assertTrue(self.partner_a.employee,
                        "biz_hr_okr: Error compute_is_employee")
