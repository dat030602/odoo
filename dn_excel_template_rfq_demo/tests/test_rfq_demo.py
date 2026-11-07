# -*- coding: utf-8 -*-
"""Test suite for dn_excel_template_rfq_demo."""

import base64
import io
import openpyxl

from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestRFQDemo(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from .. import _seed_rfq_demo_data
        _seed_rfq_demo_data(cls.env)

        cls.template = cls.env['excel.report.template'].search([
            ('name', '=', 'RFQ Hetian Summary Template')
        ], limit=1)
        cls.template_py = cls.env['excel.report.template'].search([
            ('name', '=', 'RFQ Hetian Python Code Template')
        ], limit=1)
        cls.po = cls.env['purchase.order'].search([
            ('origin', '=', 'HETIAN-DEMO-2026')
        ], limit=1)

    def test_01_demo_data_integrity(self):
        """Verify that template and demo PO records are created and populated."""
        self.assertTrue(self.template, "Hetian Excel template should exist")
        self.assertEqual(self.template.model, 'purchase.order')
        self.assertTrue(self.template.template_file, "Template file should have data")

        # Check variables and datasources
        var_names = self.template.variable_ids.mapped('name')
        for expected in ['date_order', 'date_planned', 'tax_included', 'amount_total', 'conditions']:
            self.assertIn(expected, var_names)

        self.assertTrue(self.po, "Demo PO HETIAN-DEMO-2026 should exist")
        self.assertEqual(self.po.x_studio_order_type, 'Custom Precision Production')
        self.assertEqual(self.po.x_studio_production_country_1, 'China')
        self.assertEqual(len(self.po.order_line), 3, "Demo PO should have 3 lines")

    def test_02_wizard_render(self):
        """Test wizard modal generation and verify generated Excel workbook."""
        wizard = self.env['excel.template.preview.wizard'].create({
            'order_id': self.po.id,
            'template_id': self.template.id,
        })
        self.assertEqual(wizard.state, 'draft')
        self.assertEqual(wizard.line_count, 3)

        action = wizard.action_generate_excel()
        self.assertEqual(wizard.state, 'done')
        self.assertTrue(wizard.file_data, "Generated file_data should not be empty")
        self.assertTrue(wizard.filename.endswith('.xlsx'))

        # Inspect generated workbook bytes
        raw_bytes = base64.b64decode(wizard.file_data)
        self.assertTrue(raw_bytes.startswith(b'PK'), "Output file should be a valid zip / Excel file")

        wb = openpyxl.load_workbook(io.BytesIO(raw_bytes))
        ws = wb.active
        self.assertEqual(ws['B5'].value, f"询价单 - {self.po.name}")
        self.assertEqual(ws['H13'].value, 'China')

        # Check expanded product lines
        self.assertEqual(ws['A19'].value, 'Hetian White Jade Ring Blank')
        self.assertEqual(ws['D19'].value, 'ORD-HT-001')
        self.assertEqual(ws['A20'].value, 'Precision Gold Clasp Setting HT-02')
        self.assertEqual(ws['A21'].value, 'Imperial Jade Seal Mounting Custom')

        # Check downstream shifted total row at row 22
        self.assertEqual(ws['H22'].value, self.po.currency_id.name)
        self.assertEqual(ws['I22'].value, self.po.amount_total)

        # Check downstream shifted notes at row 24 (shifted +2 from A22)
        self.assertEqual(ws['A24'].value, "Please expedite initial batch inspection before final packaging.")
        self.assertTrue(ws['A24'].alignment and ws['A24'].alignment.wrap_text)

    def test_03_po_action_open_popup(self):
        """Test action_open_excel_template_popup on purchase.order."""
        res = self.po.action_open_excel_template_popup()
        self.assertEqual(res.get('type'), 'ir.actions.act_window')
        self.assertEqual(res.get('res_model'), 'excel.template.preview.wizard')
        self.assertEqual(res.get('target'), 'new')
        self.assertEqual(res.get('context', {}).get('default_order_id'), self.po.id)
        self.assertEqual(res.get('context', {}).get('default_template_id'), self.template.id)

    def test_04_python_code_template_integrity(self):
        """Verify that Python Code template exists and has valid configuration."""
        self.assertTrue(self.template_py, "Hetian Python Code Excel template should exist")
        self.assertEqual(self.template_py.config_mode, 'code')
        self.assertEqual(self.template_py.model, 'purchase.order')
        self.assertTrue(self.template_py.python_code)
        self.assertIn("variables['tax_included']", self.template_py.python_code)
        self.assertIn("tables['summary']", self.template_py.python_code)

    def test_05_python_code_template_actions(self):
        """Test action_test_python_code and action_validate_template on Python Code template."""
        # Test code execution action
        test_act = self.template_py.action_test_python_code()
        self.assertEqual(test_act.get('type'), 'ir.actions.client')
        self.assertEqual(test_act.get('params', {}).get('type'), 'success')
        self.assertIn('summary:', test_act.get('params', {}).get('message', ''))

        # Test placeholder validation
        val_act = self.template_py.action_validate_template()
        self.assertEqual(val_act.get('type'), 'ir.actions.client')
        self.assertEqual(val_act.get('params', {}).get('type'), 'success')

    def test_06_python_code_wizard_render(self):
        """Test wizard modal generation using Python Code template and inspect workbook output."""
        wizard = self.env['excel.template.preview.wizard'].create({
            'order_id': self.po.id,
            'template_id': self.template_py.id,
        })
        self.assertEqual(wizard.state, 'draft')
        self.assertEqual(wizard.line_count, 3)

        action = wizard.action_generate_excel()
        self.assertEqual(wizard.state, 'done')
        self.assertTrue(wizard.file_data, "Generated file_data should not be empty")

        raw_bytes = base64.b64decode(wizard.file_data)
        wb = openpyxl.load_workbook(io.BytesIO(raw_bytes))
        ws = wb.active

        # Check expanded product lines from tables['summary']
        self.assertEqual(ws['A19'].value, 'Hetian White Jade Ring Blank - Grade A Cut')
        self.assertEqual(ws['D19'].value, 'ORD-HT-001')
        self.assertEqual(ws['E19'].value, 'BSK-HT-SPEC-01A')
        self.assertEqual(ws['F19'].value, 150.0)
        self.assertEqual(ws['H19'].value, 125.0)
        self.assertEqual(ws['I19'].value, 18750.0)

        self.assertEqual(ws['A20'].value, 'Precision Gold Clasp Setting HT-02')
        self.assertEqual(ws['D20'].value, 'ORD-HT-002')
        self.assertEqual(ws['F20'].value, 300.0)
        self.assertEqual(ws['H20'].value, 48.5)
        self.assertEqual(ws['I20'].value, 14550.0)

        self.assertEqual(ws['A21'].value, 'Imperial Jade Seal Mounting Custom')
        self.assertEqual(ws['D21'].value, 'ORD-HT-003')
        self.assertEqual(ws['F21'].value, 25.0)
        self.assertEqual(ws['H21'].value, 380.0)
        self.assertEqual(ws['I21'].value, 9500.0)

        # Check downstream shifted total at row 22
        self.assertEqual(ws['H22'].value, self.po.currency_id.name)
        self.assertEqual(ws['I22'].value, self.po.amount_total)

        # Check downstream shifted notes at row 24
        self.assertEqual(ws['A24'].value, "Please expedite initial batch inspection before final packaging.")
        self.assertTrue(ws['A24'].alignment and ws['A24'].alignment.wrap_text)

        # Check downstream shifted terms & conditions at row 26
        self.assertIn("1. Quality Standards:", ws['A26'].value)

    def test_07_po_action_open_python_popup(self):
        """Test action_open_excel_python_popup on purchase.order."""
        res = self.po.action_open_excel_python_popup()
        self.assertEqual(res.get('type'), 'ir.actions.act_window')
        self.assertEqual(res.get('res_model'), 'excel.template.preview.wizard')
        self.assertEqual(res.get('target'), 'new')
        self.assertEqual(res.get('context', {}).get('default_order_id'), self.po.id)
        self.assertEqual(res.get('context', {}).get('default_template_id'), self.template_py.id)
