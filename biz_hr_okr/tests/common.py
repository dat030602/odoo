from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class HrTestEmployeeCommon(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create user.
        cls.user_demo = cls.env.ref('base.user_demo')
        # User has group 'group_hr_user'
        cls.partner_a = cls.env['res.partner'].with_context(tracking_disable=True).create({
            'name': 'partner_a',
            'company_id': False
        })
        cls.employee = cls.env['hr.employee'].with_context(tracking_disable=True).create({
            'name': 'Employee',
            'address_home_id': cls.partner_a.id
            })
