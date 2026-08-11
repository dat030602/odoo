# -*- coding: utf-8 -*-
"""
test_base_excel_report.py
=========================

Integration tests for the BaseExcelReport model.

These tests require an Odoo database (TransactionCase) and test the
full pipeline: template loading → context retrieval → rendering → export.

Run with:
    odoo-bin test -i base_excel_report_v2 --test-enable -d <database>
"""

import base64
import io
from unittest.mock import patch

import openpyxl

from odoo.tests import TransactionCase
from odoo.exceptions import UserError


class TestBaseExcelReport(TransactionCase):
    """Integration tests for the base.excel.report model."""

    def setUp(self):
        super().setUp()
        # Create a test template attachment
        self.template_name = 'template_test_report.xlsx'
        self._create_template_attachment()

    def _create_template_attachment(self):
        """Create a test .xlsx template in ir.attachment."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws['A1'] = '{{ company.name }}'
        ws['A2'] = 'Report printed on {{ print_date }}'
        ws['A3'] = 'Name'
        ws['B3'] = 'Amount'
        ws['A4'] = '{% for line in lines %}'
        ws['A5'] = '{{ line.name }}'
        ws['B5'] = '{{ line.amount | fmt:#,##0.00 }}'
        ws['A6'] = '{% endfor %}'
        ws['A7'] = 'Grand Total'
        ws['B7'] = '{{ lines | sum:amount }}'

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        self.env['ir.attachment'].create({
            'name': self.template_name,
            'datas': base64.b64encode(buffer.getvalue()),
            'type': 'binary',
        })

    def _create_test_report(self):
        """Create a test report wizard instance."""
        return self.env['base.excel.report'].create({})

    def test_action_generate_excel_success(self):
        """The full pipeline generates a downloadable Excel file."""
        report = self._create_test_report()

        # Patch _get_template_name and _get_report_context
        with patch.object(
            type(report), '_get_template_name',
            return_value=self.template_name,
        ), patch.object(
            type(report), '_get_report_context',
            return_value={
                'company': {'name': 'Test Company'},
                'print_date': '01/08/2026',
                'lines': [
                    {'name': 'Order A', 'amount': 100.50},
                    {'name': 'Order B', 'amount': 200.75},
                ],
            },
        ):
            result = report.action_generate_excel()

        # Should return an act_window action
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'base.excel.report')
        self.assertEqual(result['res_id'], report.id)
        self.assertEqual(result['view_mode'], 'form')
        self.assertEqual(result['target'], 'new')

        # State should be 'download'
        self.assertEqual(report.state, 'download')

        # File should be generated
        self.assertTrue(report.excel_file)
        self.assertTrue(report.file_name)

        # Verify the generated file content
        file_data = base64.b64decode(report.excel_file)
        wb = openpyxl.load_workbook(io.BytesIO(file_data))
        ws = wb.active

        # Header
        self.assertEqual(ws.cell(row=1, column=1).value, 'Test Company')
        self.assertEqual(ws.cell(row=2, column=1).value, 'Report printed on 01/08/2026')

        # Table headers
        self.assertEqual(ws.cell(row=3, column=1).value, 'Name')
        self.assertEqual(ws.cell(row=3, column=2).value, 'Amount')

        # Loop data (2 items)
        self.assertEqual(ws.cell(row=4, column=1).value, 'Order A')
        self.assertEqual(ws.cell(row=5, column=1).value, 'Order B')

        # Grand total formula
        self.assertEqual(ws.cell(row=6, column=1).value, 'Grand Total')
        self.assertEqual(ws.cell(row=6, column=2).value, '=SUBTOTAL(9,B4:B5)')

    def test_template_not_found_raises_user_error(self):
        """A missing template attachment raises UserError."""
        report = self._create_test_report()

        with patch.object(
            type(report), '_get_template_name',
            return_value='nonexistent_template.xlsx',
        ), patch.object(
            type(report), '_get_report_context',
            return_value={'lines': []},
        ):
            with self.assertRaises(UserError):
                report.action_generate_excel()

    def test_context_not_dict_raises_user_error(self):
        """A non-dict context raises UserError."""
        report = self._create_test_report()

        with patch.object(
            type(report), '_get_template_name',
            return_value=self.template_name,
        ), patch.object(
            type(report), '_get_report_context',
            return_value=[{'name': 'A'}],  # list, not dict
        ):
            with self.assertRaises(UserError):
                report.action_generate_excel()

    def test_template_error_raises_user_error(self):
        """A TemplateError is caught and re-raised as UserError."""
        report = self._create_test_report()

        # Create a template with an unclosed for block
        wb = openpyxl.Workbook()
        ws = wb.active
        ws['A1'] = '{% for line in lines %}'
        ws['A2'] = '{{ line.name }}'
        # Missing {% endfor %}

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        self.env['ir.attachment'].create({
            'name': 'template_bad.xlsx',
            'datas': base64.b64encode(buffer.getvalue()),
            'type': 'binary',
        })

        with patch.object(
            type(report), '_get_template_name',
            return_value='template_bad.xlsx',
        ), patch.object(
            type(report), '_get_report_context',
            return_value={'lines': [{'name': 'A'}]},
        ):
            with self.assertRaises(UserError):
                report.action_generate_excel()

    def test_output_filename_default(self):
        """The default output filename is derived from the template name."""
        report = self._create_test_report()

        with patch.object(
            type(report), '_get_template_name',
            return_value='template_sale_report.xlsx',
        ):
            filename = report._get_output_filename()

        self.assertEqual(filename, 'sale_report_output.xlsx')

    def test_output_filename_custom(self):
        """A custom output filename override works."""
        report = self._create_test_report()

        with patch.object(
            type(report), '_get_template_name',
            return_value='template_sale_report.xlsx',
        ), patch.object(
            type(report), '_get_output_filename',
            return_value='Custom_Report_2026.xlsx',
        ):
            filename = report._get_output_filename()

        self.assertEqual(filename, 'Custom_Report_2026.xlsx')
