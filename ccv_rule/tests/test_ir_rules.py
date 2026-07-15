# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestIrRules(TransactionCase):
    """Test cases for ir.rule functionality"""

    def setUp(self):
        super(TestIrRules, self).setUp()
        
        # Tạo test users
        self.mrp_manager = self.env['res.users'].create({
            'name': 'MRP Manager Test',
            'login': 'mrp_manager_test',
            'email': 'mrp_manager@test.com',
            'groups_id': [(4, self.env.ref('mrp.group_mrp_manager').id)]
        })
        
        self.mrp_user = self.env['res.users'].create({
            'name': 'MRP User Test',
            'login': 'mrp_user_test',
            'email': 'mrp_user@test.com',
            'groups_id': [(4, self.env.ref('mrp.group_mrp_user').id)]
        })
        
        # self.purchase_manager = self.env['res.users'].create({
        #     'name': 'Purchase Manager Test',
        #     'login': 'purchase_manager_test',
        #     'email': 'purchase_manager@test.com',
        #     'groups_id': [(4, self.env.ref('purchase.group_purchase_manager').id)]
        # })
        
        # self.purchase_user = self.env['res.users'].create({
        #     'name': 'Purchase User Test',
        #     'login': 'purchase_user_test',
        #     'email': 'purchase_user@test.com',
        #     'groups_id': [(4, self.env.ref('purchase.group_purchase_user').id)]
        # })

    def test_mrp_production_rules(self):
        """Test MRP Production rules"""
        
        # Tạo test MO
        mo_done = self.env['mrp.production'].create({
            'name': 'MO/TEST/001',
            'product_id': self.env.ref('product.product_product_4').id,
            'product_qty': 10,
            'state': 'done'
        })
        
        mo_draft = self.env['mrp.production'].create({
            'name': 'MO/TEST/002',
            'product_id': self.env.ref('product.product_product_4').id,
            'product_qty': 5,
            'state': 'draft'
        })
        
        # Test MRP Manager - có thể xem tất cả
        with self.env.do_in_onchange():
            self.env = self.env(user=self.mrp_manager)
            all_mos = self.env['mrp.production'].search([])
            self.assertIn(mo_done.id, all_mos.ids)
            self.assertIn(mo_draft.id, all_mos.ids)
        
        # Test MRP User - chỉ xem MO chưa done
        with self.env.do_in_onchange():
            self.env = self.env(user=self.mrp_user)
            user_mos = self.env['mrp.production'].search([])
            self.assertNotIn(mo_done.id, user_mos.ids)
            self.assertIn(mo_draft.id, user_mos.ids)

    # def test_purchase_order_rules(self):
    #     """Test Purchase Order rules"""
        
    #     # Tạo test PO
    #     po_manager = self.env['purchase.order'].create({
    #         'partner_id': self.env.ref('base.res_partner_1').id,
    #         'user_id': self.purchase_manager.id,
    #     })
        
    #     po_user = self.env['purchase.order'].create({
    #         'partner_id': self.env.ref('base.res_partner_2').id,
    #         'user_id': self.purchase_user.id,
    #     })
        
    #     # Test Purchase Manager - có thể xem tất cả
    #     with self.env.do_in_onchange():
    #         self.env = self.env(user=self.purchase_manager)
    #         all_pos = self.env['purchase.order'].search([])
    #         self.assertIn(po_manager.id, all_pos.ids)
    #         self.assertIn(po_user.id, all_pos.ids)
        
    #     # Test Purchase User - chỉ xem PO của mình
    #     with self.env.do_in_onchange():
    #         self.env = self.env(user=self.purchase_user)
    #         user_pos = self.env['purchase.order'].search([])
    #         self.assertNotIn(po_manager.id, user_pos.ids)
    #         self.assertIn(po_user.id, user_pos.ids)

    def test_rule_creation(self):
        """Test that rules are created correctly"""
        
        # Kiểm tra MRP rules
        mrp_manager_rule = self.env['ir.rule'].search([
            ('name', '=', 'MRP Manager can see all MO')
        ])
        self.assertTrue(mrp_manager_rule)
        self.assertEqual(mrp_manager_rule.domain_force, '[(1,\'=\',1)]')
        
        mrp_user_rule = self.env['ir.rule'].search([
            ('name', '=', 'Hide Done MO for non-managers')
        ])
        self.assertTrue(mrp_user_rule)
        self.assertEqual(mrp_user_rule.domain_force, '[(\'state\',\'!=\',\'done\')]')
        
        # Kiểm tra Purchase rules
        # purchase_manager_rule = self.env['ir.rule'].search([
        #     ('name', '=', 'Purchase Manager can see all PO')
        # ])
        # self.assertTrue(purchase_manager_rule)
        
        # purchase_user_rule = self.env['ir.rule'].search([
        #     ('name', '=', 'Purchase User can see own PO')
        # ])
        # self.assertTrue(purchase_user_rule)
        # self.assertEqual(purchase_user_rule.domain_force, '[(\'user_id\',\'=\',user.id)]')

    def test_rule_groups(self):
        """Test that rules have correct groups assigned"""
        
        # MRP Manager rule
        mrp_manager_rule = self.env['ir.rule'].search([
            ('name', '=', 'MRP Manager can see all MO')
        ])
        self.assertTrue(mrp_manager_rule)
        self.assertIn(
            self.env.ref('mrp.group_mrp_manager').id,
            mrp_manager_rule.groups.ids
        )
        
        # Purchase User rule
        # purchase_user_rule = self.env['ir.rule'].search([
        #     ('name', '=', 'Purchase User can see own PO')
        # ])
        # self.assertTrue(purchase_user_rule)
        # self.assertIn(
        #     self.env.ref('purchase.group_purchase_user').id,
        #     purchase_user_rule.groups.ids
        # )
