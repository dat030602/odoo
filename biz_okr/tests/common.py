from odoo.tests.common import TransactionCase


class Common(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super(Common, cls).setUpClass()
        cls.no_mailthread_features_ctx = {
            'no_reset_password': True,
            'tracking_disable': True,
        }
        cls.env = cls.env(context=dict(cls.no_mailthread_features_ctx, **cls.env.context))
        
        cls.okr_manager = cls.env['res.users'].create({
            'name': 'Okr manager',
            'login': 'okr manager',
            'groups_id': [(6, 0, [cls.env.ref('biz_okr.group_okr_manager').id])]
        })
        cls.hr_manager_user = cls.env['res.users'].create({
            'name': 'HR Manager',
            'login': 'hr manager',
            'groups_id': [(6, 0, [cls.env.ref('biz_okr.group_okr_user').id])]
        })
        cls.hr_user = cls.env['res.users'].create({
            'name': 'hr user',
            'login': 'hr user',
            'groups_id': [(6, 0, [cls.env.ref('biz_okr.group_okr_user').id])]
        })
        cls.user1 = cls.env['res.users'].create({
            'name': 'user1 test ',
            'login': 'user1 test',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        
        cls.hr_department = cls.env['hr.department'].create({
            'name': 'HR Department'
        })
        
        cls.hr_manager_employee = cls.env['hr.employee'].create({
            'name': 'HR Manager Employee',
            'user_id': cls.hr_manager_user.id
        })
        cls.hr_employee = cls.env['hr.employee'].create({
            'name': 'Employee 1',
            'user_id': cls.hr_user.id,
            'parent_id': cls.hr_manager_employee.id
        })
        cls.user1_employee = cls.env['hr.employee'].create({
            'name': 'user1 test ',
            'user_id': cls.user1.id
        })
        cls.hr_department.manager_id = cls.hr_manager_employee.id 
        
        cls.okr_node_root = cls.env['okr.node'].with_user(cls.okr_manager).create({
            'name': 'OKR Root Test',
            'mode': 'company',
        })
        cls.child_ids = cls.env['okr.node'].create([
            {'name': 'Recruited 2 accountant'},
            {'name': 'Recruited recruited 3 managers'},
            {'name': 'Recruited 5 employees'}
        ])
