from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from .common import Common


@tagged('post_install', '-at_install', 'access_rights')
class TestAccessRight(Common):

    @classmethod
    def setUpClass(cls):
        super(TestAccessRight, cls).setUpClass()

        cls.company1 = cls.env['res.company'].create({
            'name': 'company 1'
        })
        cls.company2 = cls.env['res.company'].create({
            'name': 'company 2'
        })

        cls.company1_user1 = cls.env['res.users'].create({
            'name': 'user1',
            'login': 'user test 1',
            'groups_id': [(6, 0, [cls.env.ref('biz_okr.group_okr_manager').id])],
            'company_id': cls.company1.id,
            'company_ids': [(6, 0, cls.company1.ids)],
        })
        cls.company2_user2 = cls.env['res.users'].create({
            'name': 'user2',
            'login': 'user test 2',
            'groups_id': [(6, 0, [cls.env.ref('biz_okr.group_okr_manager').id])],
            'company_id': cls.company2.id,
            'company_ids': [(6, 0, cls.company2.ids)]
        })
        cls.multi_company_user3 = cls.env['res.users'].create({
            'name': 'user3',
            'login': 'user test 3',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
            'company_id': cls.company1.id,
            'company_ids': [(6, 0, [cls.company1.id, cls.company2.id])]
        })

        cls.env['hr.employee'].create({
            'name': 'user 1',
            'company_id': cls.company1.id,
            'user_id': cls.company1_user1.id
        })
        cls.env['hr.employee'].create({
            'name': 'user 2',
            'company_id': cls.company2.id,
            'user_id': cls.company2_user2.id
        })

        cls.okr_1 = cls.env['okr.node'].with_user(cls.company1_user1).create({
            'name': 'okr 1'
        })
        cls.okr_2 = cls.env['okr.node'].with_user(cls.company2_user2).create({
            'name': 'okr 2'
        })

    def test_01_access_right(self):
        """ User does not have OKR rights, is an employee of a department """
        self.okr_node_root.with_user(self.user1).read()

        okr_test1 = self.env['okr.node'].with_user(self.user1).create({
            'name': 'okr test 1',
            'parent_id': self.okr_node_root.id,
            'user_id': self.user1.id,
        })
        okr_test1.with_user(self.user1).name = 'test'
        okr_test1.with_user(self.user1).unlink()

        okr_test2 = self.okr_node_root.with_user(self.user1)
        with self.assertRaises(AccessError):
            okr_test2.name = 'test'
        with self.assertRaises(AccessError):
            okr_test2.unlink()

        with self.assertRaises(AccessError):
            okr_test2.button_confirm()
        with self.assertRaises(AccessError):
            okr_test2.button_cancel()
        with self.assertRaises(AccessError):
            okr_test2.action_set_to_draft()

    def test_02_access_right(self):
        """ User has OKR User rights, is an employee of a department """
        self.okr_node_root.with_user(self.hr_user).read()

        okr_test1 = self.env['okr.node'].with_user(self.hr_manager_user).create({
            'name': 'okr 1',
            'parent_id': self.okr_node_root.id,
            'user_id': self.hr_manager_user.id,
            'mode': 'department'
        })

        okr_test1.with_user(self.hr_user).name = 'test 1'
        okr_test1.with_user(self.hr_user).unlink()

        with self.assertRaises(AccessError):
            self.okr_node_root.with_user(self.hr_user).name = 'test'

    def test_03_access_right(self):
        """ User has OKR Administrator rights, is an employee of a department """
        self.hr_user.groups_id = [(6, 0, [self.env.ref('biz_okr.group_okr_manager').id])]

        okr_test1 = self.env['okr.node'].with_user(self.user1).create({
            'name': 'okr test1',
            'parent_id': self.okr_node_root.id
        }).with_user(self.hr_user)
        okr_test2 = self.env['okr.node'].with_user(self.okr_manager).create({
            'name': 'okr test2'
        }).with_user(self.hr_user)

        okr_test1.name = 'test1'
        okr_test1.unlink()

        okr_test2.name = 'test1'
        okr_test2.unlink()

    def test_01_multi_companies(self):
        """
        case 1: User A in company 1 has no rights to the okr node in company 2 if user A is not in company 2.
        """
        # case 1:
        with self.assertRaises(AccessError):
            self.okr_1.with_user(self.company2_user2).read()
        with self.assertRaises(AccessError):
            self.okr_1.with_user(self.company2_user2).name = 'test'
        with self.assertRaises(AccessError):
            self.okr_1.with_user(self.company2_user2).unlink()

        with self.assertRaises(AccessError):
            self.okr_2.with_user(self.company1_user1).read()
        with self.assertRaises(AccessError):
            self.okr_2.with_user(self.company1_user1).name = 'test'
        with self.assertRaises(AccessError):
            self.okr_2.with_user(self.company1_user1).unlink()

    def test_02_multi_companies(self):
        """
        case 2: Users belonging to multiple companies can view all OKRs belonging to those companies.
                Permissions to write, create, and delete remain the same.
        """
        okr_3 = self.okr_1.copy()
        okr_4 = self.okr_2.copy()

        self.okr_1.with_user(self.company1_user1).read()
        self.okr_1.with_user(self.company1_user1).name = 'test'
        self.okr_1.with_user(self.company1_user1).unlink()

        self.okr_2.with_user(self.company2_user2).read()
        self.okr_2.with_user(self.company2_user2).name = 'test'
        self.okr_2.with_user(self.company2_user2).unlink()

        # case 2:
        okr_3.with_user(self.multi_company_user3).read()
        okr_4.with_user(self.multi_company_user3).read()

        with self.assertRaises(AccessError):
            okr_3.with_user(self.multi_company_user3).name = 'test'
        with self.assertRaises(AccessError):
            okr_4.with_user(self.multi_company_user3).name = 'test'
