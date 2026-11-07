# -*- coding: utf-8 -*-
"""
Odoo TransactionCase Integration Tests for dn_excel_template_report.
Verifies model CRUD, dynamic action binding, template rendering, file validation,
multi-company rule isolation, and access control.
"""
import base64
import os
import unittest

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, AccessError, UserError


@tagged('post_install', '-at_install')
class TestExcelTemplateReport(TransactionCase):
    """
    Integration test suite executing inside Odoo 19 environment with database rollback.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template_model = cls.env['excel.report.template']
        cls.variable_model = cls.env['excel.report.variable']
        cls.datasource_model = cls.env['excel.report.datasource']
        cls.column_model = cls.env['excel.report.datasource.column']
        cls.python_module_model = cls.env['excel.report.python.module']

        fixture_path = os.path.join(
            os.path.dirname(__file__),
            'fixtures',
            'TEMPLATE.xlsx'
        )
        with open(fixture_path, 'rb') as f:
            cls.fixture_bytes = f.read()

        cls.po_model = cls.env['ir.model'].search([('model', '=', 'purchase.order')], limit=1)

        # Setup vendor partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Sample Supplier Co',
        })

        # Setup UoM
        cls.product_uom = cls.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        if not cls.product_uom:
            cls.product_uom = cls.env['uom.uom'].search([], limit=1)

        # Setup Products
        cls.product_1 = cls.env['product.product'].create({
            'name': 'Widget Metal A',
            'uom_id': cls.product_uom.id,
        })
        cls.product_2 = cls.env['product.product'].create({
            'name': 'Widget Metal B',
            'uom_id': cls.product_uom.id,
        })

        # Setup Purchase Order (RFQ)
        cls.po = cls.env['purchase.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [
                (0, 0, {
                    'product_id': cls.product_1.id,
                    'product_qty': 10.0,
                    'price_unit': 50.0,
                    'name': 'Widget Metal A',
                }),
                (0, 0, {
                    'product_id': cls.product_2.id,
                    'product_qty': 20.0,
                    'price_unit': 80.0,
                    'name': 'Widget Metal B',
                }),
            ],
        })

    def test_01_template_crud_and_binding(self):
        """
        Verify template creation on purchase.order, action_bind_print_button,
        binding_action_id registration, and action_unbind_print_button.
        """
        template = self.template_model.create({
            'name': 'RFQ Summary Report',
            'model_id': self.po_model.id,
            'template_file': base64.b64encode(self.fixture_bytes),
            'template_filename': 'TEMPLATE.xlsx',
            'empty_table_policy': 'keep_blank',
            'filename_expr': "'RFQ_%s' % record.name",
        })
        self.assertTrue(template.id)
        self.assertEqual(template.model, 'purchase.order')

        # Bind Print Action to target model
        template.action_bind_print_button()
        self.assertTrue(template.binding_action_id)
        self.assertEqual(template.binding_action_id.binding_model_id.model, 'purchase.order')
        self.assertEqual(template.binding_action_id.binding_type, 'report')

        # Unbind Action
        template.action_unbind_print_button()
        self.assertFalse(template.binding_action_id)

    def test_01b_python_module_whitelist(self):
        """Only enabled modules are exposed, and the test button enables installed modules."""
        template = self.template_model.create({
            'name': 'Whitelist Test Report',
            'model_id': self.po_model.id,
            'template_file': base64.b64encode(self.fixture_bytes),
            'template_filename': 'TEMPLATE.xlsx',
        })
        module = self.python_module_model.create({'name': 'json'})
        self.assertFalse(module.active)
        module.action_test_module()
        self.assertTrue(module.active)

        context = template._get_python_eval_context(record=self.po)
        self.assertIsNotNone(context['allowed_modules']['json'])
        with self.assertRaises(UserError):
            context['_dynamic_import']('os')

    def test_02_render_record_success(self):
        """
        Verify end-to-end report rendering on single purchase.order record
        with configured variables and datasources, returning valid PKZip bytes.
        """
        template = self.template_model.create({
            'name': 'RFQ Summary Report',
            'model_id': self.po_model.id,
            'template_file': base64.b64encode(self.fixture_bytes),
            'template_filename': 'TEMPLATE.xlsx',
            'empty_table_policy': 'keep_blank',
        })

        # Add custom variable
        self.variable_model.create({
            'template_id': template.id,
            'name': 'conditions',
            'code': "'Payment within 30 days.'",
            'value_type': 'text',
        })

        # Add datasource
        ds = self.datasource_model.create({
            'template_id': template.id,
            'name': 'summary',
            'rows_expr': 'record.order_line',
        })

        # Add datasource columns
        self.column_model.create([
            {
                'datasource_id': ds.id,
                'key': 'product',
                'expr': 'line.product_id.display_name',
            },
            {
                'datasource_id': ds.id,
                'key': 'order_number',
                'expr': 'record.name',
            },
            {
                'datasource_id': ds.id,
                'key': 'design',
                'expr': "'D-01'",
            },
            {
                'datasource_id': ds.id,
                'key': 'quantity',
                'expr': 'line.product_qty',
            },
            {
                'datasource_id': ds.id,
                'key': 'uom',
                'expr': 'line.product_uom_id.name',
            },
            {
                'datasource_id': ds.id,
                'key': 'price',
                'expr': 'line.price_unit',
            },
        ])

        rendered_bytes = template.render_record(self.po, strict=True)
        self.assertTrue(rendered_bytes)
        self.assertTrue(rendered_bytes.startswith(b'PK'), "Rendered report must start with PKZip signature")

    def test_03_invalid_file_rejected(self):
        """
        Verify template constraints reject corrupted files, non-xlsx files, and .xlsm macros.
        """
        # 1. Non-Excel raw text file
        with self.assertRaises(ValidationError):
            self.template_model.create({
                'name': 'Bad File Template',
                'model_id': self.po_model.id,
                'template_file': base64.b64encode(b'Not an excel file'),
                'template_filename': 'bad.txt',
            })

        # 2. Macro-enabled .xlsm rejection
        with self.assertRaises(ValidationError):
            self.template_model.create({
                'name': 'Macro Template',
                'model_id': self.po_model.id,
                'template_file': base64.b64encode(self.fixture_bytes),
                'template_filename': 'template.xlsm',
            })

    def test_04_multi_company_isolation(self):
        """
        Verify multi-company record rules isolate templates between companies.
        """
        company_2 = self.env['res.company'].create({'name': 'Branch Company 2'})
        template = self.template_model.create({
            'name': 'Branch 2 Report',
            'model_id': self.po_model.id,
            'template_file': base64.b64encode(self.fixture_bytes),
            'template_filename': 'template.xlsx',
            'company_id': company_2.id,
        })

        # Multi-company record rules are evaluated for non-superuser users
        user_c1 = self.env['res.users'].create({
            'name': 'Company 1 User',
            'login': 'c1_user_test',
            'email': 'c1_user_test@example.com',
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        user_c2 = self.env['res.users'].create({
            'name': 'Company 2 User',
            'login': 'c2_user_test',
            'email': 'c2_user_test@example.com',
            'company_id': company_2.id,
            'company_ids': [(6, 0, [company_2.id])],
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        # Query under default company user (company_1) -> should be isolated by record rule
        templates_company_1 = self.template_model.with_user(user_c1).search([('id', '=', template.id)])
        self.assertFalse(templates_company_1, "Template restricted to company 2 must not be visible to company 1")

        # Query under company_2 user -> visible
        templates_company_2 = self.template_model.with_user(user_c2).search([('id', '=', template.id)])
        self.assertTrue(templates_company_2, "Template restricted to company 2 must be visible within company 2")

    def test_05_security_access_rights(self):
        """
        Verify security group enforcement on report download action.
        """
        test_group = self.env['res.groups'].create({'name': 'Test Restricted Group'})
        template = self.template_model.create({
            'name': 'Restricted Report',
            'model_id': self.po_model.id,
            'template_file': base64.b64encode(self.fixture_bytes),
            'template_filename': 'template.xlsx',
            'group_ids': [(6, 0, [test_group.id])],
        })

        test_user = self.env['res.users'].create({
            'name': 'Standard Employee',
            'login': 'std_emp_test',
            'email': 'std_emp@example.com',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        # Non-member user should be denied report download action
        with self.assertRaises(AccessError):
            template.with_user(test_user).action_open_download([self.po.id])

        # Adding user to group grants download access
        test_user.write({'group_ids': [(4, test_group.id)]})
        action = template.with_user(test_user).action_open_download([self.po.id])
        self.assertEqual(action.get('type'), 'ir.actions.act_url')
        self.assertIn('/excel_template_report/download', action.get('url'))

    def test_06_python_code_script_mode(self):
        """
        Verify Python Code script execution mode (config_mode='code').
        Tests helper injection (format_date, format_amount, html2plaintext),
        action_test_python_code(), action_validate_template(), and render_record().
        """
        import io
        import openpyxl

        code_script = """
variables['tax_included'] = 'YES_TAX'
variables['conditions'] = 'Payment within 30 days.'
variables['formatted_date'] = format_date(record.date_order, '%d/%m/%Y')
variables['formatted_total'] = format_amount(record.amount_total, record.currency_id)
variables['plain_notes'] = html2plaintext('<p>Urgent <b>Delivery</b></p>')

tables['summary'] = [
    {
        'product': line.name,
        'quantity': line.product_qty,
        'price': line.price_unit,
        'order_number': 'ORD-%d' % idx,
        'design': 'STD',
        'uom': (line.product_uom_id.name if hasattr(line, 'product_uom_id') and line.product_uom_id else (line.product_id.uom_id.name if line.product_id else 'Units')),
    }
    for idx, line in enumerate(record.order_line, start=1)
]
"""
        template = self.template_model.create({
            'name': 'Python Code Script RFQ Template',
            'model_id': self.po_model.id,
            'config_mode': 'code',
            'template_file': base64.b64encode(self.fixture_bytes),
            'template_filename': 'template.xlsx',
            'python_code': code_script,
        })

        # 1. Test action_test_python_code button
        test_res = template.action_test_python_code()
        self.assertEqual(test_res.get('type'), 'ir.actions.client')
        self.assertEqual(test_res.get('params', {}).get('type'), 'success')
        self.assertIn('summary:', test_res.get('params', {}).get('message', ''))

        # 2. Test action_validate_template
        val_res = template.action_validate_template()
        self.assertEqual(val_res.get('type'), 'ir.actions.client')
        self.assertEqual(val_res.get('params', {}).get('type'), 'success')

        # 3. Test render_record
        rendered_bytes = template.render_record(self.po)
        self.assertTrue(len(rendered_bytes) > 0)

        wb = openpyxl.load_workbook(io.BytesIO(rendered_bytes))
        ws = wb['RFQ']

        # Verify loop rows populated from tables['summary']
        self.assertEqual(ws['A19'].value, 'Widget Metal A')
        self.assertEqual(ws['F19'].value, 10.0)
        self.assertEqual(ws['A20'].value, 'Widget Metal B')
        self.assertEqual(ws['F20'].value, 20.0)

        # 4. Test error handling on bad python code
        template.python_code = "raise ValueError('Custom test error')"
        with self.assertRaises(UserError) as cm:
            template._execute_python_request(record=self.po, for_check=True)
        self.assertIn("Custom test error", str(cm.exception))
