from odoo.tests import tagged

from .common import HrTestEmployeeCommon


@tagged('post_install', '-at_install')
class TestHremployee(HrTestEmployeeCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Employee = cls.env['hr.employee'].with_context(tracking_disable=True)
        cls.ceo = Employee.create({
            'name': 'CEO',
            })
        cls.department_bod = cls.env['hr.department'].create({'name': 'Board of Directors 1', 'manager_id': cls.ceo.id})
        cls.department_sale = cls.env['hr.department'].create({'name': 'Sales 1', 'parent_id': cls.department_bod.id})
        cls.manager_l1 = Employee.create({
            'name': 'Manager Level 1',
            })
        cls.manager_l2 = Employee.create({
            'name': 'Manager Level 2',
            })
        cls.manager_l3 = Employee.create({
            'name': 'Manager Level 3',
            })

    def test_01_department_manager(self):
        """
        Sales Department Manager should take CEO as its manager
        """
        self.department_sale.manager_id = self.manager_l2
        self.manager_l2.department_id = self.department_sale
        self.assertTrue(self.manager_l2.parent_id == self.ceo)

    def test_01_recursive_managers(self):
        """
        Simple manager tree: manager_l1 => manager_l2 => manager_l3
        """
        self.manager_l1.parent_id = self.manager_l2
        self.manager_l2.parent_id = self.manager_l3
        self.assertRecordValues(
            self.manager_l1.parent_ids,
            [
                {
                    'id': self.manager_l2.id,
                    'parent_id': self.manager_l3.id
                    },
                {
                    'id': self.manager_l3.id,
                    'parent_id': False
                    }
                ]
            )
        self.assertEqual(self.manager_l1.parent_all_count, 2)
        self.assertEqual(self.manager_l2.parent_all_count, 1)
        self.assertEqual(self.manager_l3.parent_all_count, 0)

    def test_02_recursive_managers(self):
        """
        recursive mamager tree
        manager_l1 => manager_l2 => manager_l3 => manager_l1 -----
        ^                                                        |
        |---------------------------------------------------------

        1. Each will have 2 manager
        2. manager_l1 should not be a manager of itself
        """
        self.manager_l1.parent_id = self.manager_l2
        self.manager_l2.parent_id = self.manager_l3
        self.manager_l3.parent_id = self.manager_l1
        self.assertRecordValues(
            self.manager_l1.parent_ids,
            [
                {
                    'id': self.manager_l2.id,
                    'parent_id': self.manager_l3.id
                    },
                {
                    'id': self.manager_l3.id,
                    'parent_id': self.manager_l1.id
                    }
                ]
            )
        self.assertEqual(self.manager_l1.parent_all_count, 2)
        self.assertEqual(self.manager_l2.parent_all_count, 2)
        self.assertEqual(self.manager_l3.parent_all_count, 2)
        
    def test_03_recursive_managers(self):
        """
        Parent Tree: manager_l1 => manager_l2 => manager_l3
        Department Manager:
            BoD:
                manager: ceo
                member: manager_l3
            Sales:
                manager: manager_l2
                members: manager_l1, employee
        Expected: employee has 2 managers: manager_l2 and ceo
        """
        self.manager_l3.department_id = self.department_bod
        self.department_sale.manager_id = self.manager_l2
        self.manager_l1.department_id = self.department_sale
        self.employee.department_id = self.department_sale
        self.assertRecordValues(
                self.employee.parent_ids,
                [
                    {
                        'id': self.manager_l2.id
                        },
                    {
                        'id': self.ceo.id
                        }
                    ]
                )
        self.assertEqual(self.employee.parent_all_count, 2, "The Employee should have 2 managers")
        # in case we force the employee's manager on his profile as False,
        # he should still have 2 managers (his department manager - Sale, and the superior department manager - CEO)
        with self.env.cr.savepoint():
            self.employee.parent_id = False
            self.assertRecordValues(
                self.employee.parent_ids,
                [
                    {
                        'id': self.manager_l2.id
                        },
                    {
                        'id': self.ceo.id
                        }
                    ]
                )
            self.assertEqual(self.employee.parent_all_count, 2, "The Employee should have 2 managers")

    def test_01_recursive_managers_index_order(self):
        """
        managers are sorted from lower level to higher level in employee.parent_ids
        """
        self.manager_l1.parent_id = self.manager_l2
        self.manager_l2.parent_id = self.manager_l3
        self.employee.parent_id = self.manager_l1
        self.assertRecordValues(
            self.employee.parent_ids,
            [
                {
                    'id': self.manager_l1.id,
                    'parent_id': self.manager_l2.id
                    },
                {
                    'id': self.manager_l2.id,
                    'parent_id': self.manager_l3.id
                    },
                {
                    'id': self.manager_l3.id,
                    'parent_id': False
                    }
                ]
            )
        self.assertEqual(self.employee.parent_all_count, 3)
        self.assertEqual(self.manager_l1.parent_all_count, 2)
        self.assertEqual(self.manager_l2.parent_all_count, 1)
        self.assertEqual(self.manager_l3.parent_all_count, 0)

    def test_02_recursive_managers_index_order(self):
        self.department_sale.manager_id = self.manager_l2
        (self.employee + self.manager_l1).write({
            'department_id': self.department_sale.id
            })
        self.manager_l3.department_id = self.department_bod
        self.assertRecordValues(
            self.employee.parent_ids,
            [
                {
                    'id': self.manager_l2.id,
                    'parent_id': False,  # manager_l2 has no parent as he belongs to no department
                    'parent_ids': self.ceo.ids
                    },
                {
                    'id': self.ceo.id,
                    'parent_id': False,
                    'parent_ids': []
                    }
                ]
            )
        self.manager_l2.department_id = self.department_sale
        self.assertRecordValues(
            self.manager_l1.parent_ids,
            [
                {
                    'id': self.manager_l2.id,
                    'parent_id': self.ceo.id,
                    'parent_ids': self.ceo.ids
                    },
                {
                    'id': self.ceo.id,
                    'parent_id': False,
                    'parent_ids': []
                    }
                ]
            )

    def test_03_recursive_managers_index_order(self):
        self.department_sale.manager_id = self.manager_l2
        (self.employee + self.manager_l1 + self.manager_l2).write({
            'department_id': self.department_sale.id
            })
        self.employee.parent_id = self.manager_l1
        self.manager_l3.department_id = self.department_bod

        self.assertRecordValues(
            self.employee.parent_ids,
            [
                {
                    'id': self.manager_l1.id,
                    'parent_id': self.manager_l2.id,
                    'parent_ids': (self.manager_l2 + self.ceo).ids
                    },
                {
                    'id': self.manager_l2.id,
                    'parent_id': self.ceo.id,
                    'parent_ids': self.ceo.ids
                    },
                {
                    'id': self.ceo.id,
                    'parent_id': False,
                    'parent_ids': []
                    }
                ]
            )

