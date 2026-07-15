from odoo.tests import tagged
from odoo.exceptions import AccessError

from .common import HrTestEmployeeCommon


@tagged('post_install', '-at_install')
class TestHremployee(HrTestEmployeeCommon):

    def test_hr_officer(self):
        # Check features allow Hr'Officer update the fields 'Phone', 'mobile, 'email', 'name', ... on partner of others employees.
        self.user_demo.write({'groups_id': [(6, 0, [
            self.env.ref('hr.group_hr_user').id,
            self.env.ref('base.group_private_addresses').id,
            self.env.ref('base.group_partner_manager').id,
        ])]})
        partner = self.user_demo.employee_id.address_home_id
        self.assertTrue(partner.with_user(self.user_demo).write({'mobile': '0988888888'}),
                        "Hr'Officer does not update information private address on the partner of other employees.")

    def test_hr_administrator(self):
        # Check features allow Hr'Administrator update the fields 'Phone', 'mobile, 'email', 'name', ... on partner of others employees.
        self.user_demo.write({'groups_id': [(6, 0, [
            self.env.ref('hr.group_hr_manager').id,
            self.env.ref('base.group_private_addresses').id,
            self.env.ref('base.group_partner_manager').id,
        ])]})
        partner = self.user_demo.employee_id.address_home_id
        self.assertTrue(partner.with_user(self.user_demo).write({'mobile': '098888999'}),
                        "Hr'Administrator does not update information private address on the partner of other employees.")

    def test_user(self):
        # Check features not allow User update the fields 'Phone', 'mobile, 'email', 'name', ... on partner of others employees.
        self.user_demo.write(
            {'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]})
        partner = self.user_demo.employee_id.address_home_id
        with self.assertRaises(AccessError):
            partner.with_user(self.user_demo).write({'mobile': '098888999'})

        # Check access read with user
        with self.assertRaises(AccessError):
            partner.with_user(self.user_demo).read(
                ['mobile', 'email', 'phone'])
