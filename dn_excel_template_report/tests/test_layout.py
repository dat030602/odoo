# -*- coding: utf-8 -*-
"""
Pure Python Standalone Unit Tests for Layout Shift Engine (Section 7.2)
Zero ORM dependency - runs directly with openpyxl on Python 3.12.
"""
import io
import os
import sys
import time
import unittest
from io import BytesIO

import openpyxl
from openpyxl.styles import Border

# Ensure dev/dn_excel_template_report directory is on sys.path for standalone imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.dirname(CURRENT_DIR)
if MODULE_DIR not in sys.path:
    sys.path.insert(0, MODULE_DIR)

try:
    from services.parser import scan_sheet
    from services.layout import expand_loop_row, fill_loop_rows, ensure_cell_wrap_text
    from services.formula import adjust_all_formulas
    from services.resolver import to_cell_value, is_html, normalize_html
    from services.evaluator import build_eval_context
    from services.renderer import render_template
except ImportError:
    try:
        from dn_excel_template_report.services.parser import scan_sheet
        from dn_excel_template_report.services.layout import expand_loop_row, fill_loop_rows, ensure_cell_wrap_text
        from dn_excel_template_report.services.formula import adjust_all_formulas
        from dn_excel_template_report.services.resolver import to_cell_value, is_html, normalize_html
        from dn_excel_template_report.services.evaluator import build_eval_context
        from dn_excel_template_report.services.renderer import render_template
    except ImportError:
        try:
            from odoo.addons.dn_excel_template_report.services.parser import scan_sheet
            from odoo.addons.dn_excel_template_report.services.layout import expand_loop_row, fill_loop_rows, ensure_cell_wrap_text
            from odoo.addons.dn_excel_template_report.services.formula import adjust_all_formulas
            from odoo.addons.dn_excel_template_report.services.resolver import to_cell_value, is_html, normalize_html
            from odoo.addons.dn_excel_template_report.services.evaluator import build_eval_context
            from odoo.addons.dn_excel_template_report.services.renderer import render_template
        except ImportError:
            scan_sheet = None
            expand_loop_row = None
            fill_loop_rows = None
            adjust_all_formulas = None
            to_cell_value = None
            is_html = None
            normalize_html = None
            ensure_cell_wrap_text = None
            build_eval_context = None
            render_template = None

FIXTURE_PATH = os.path.join(CURRENT_DIR, 'fixtures', 'TEMPLATE.xlsx')


class TestLayoutEngine(unittest.TestCase):
    """
    Test suite verifying Section 7.2 layout shifts, row duplication, formula translation,
    and metadata restoration across table loop expansions.
    """

    def load_fixture(self):
        """Loads a clean copy of the reference RFQ workbook fixture from disk."""
        self.assertTrue(os.path.exists(FIXTURE_PATH), f"Fixture not found at {FIXTURE_PATH}")
        with open(FIXTURE_PATH, 'rb') as f:
            return openpyxl.load_workbook(BytesIO(f.read()))

    def test_n_equals_1_no_layout_change(self):
        """
        Edge Case N = 1: Single data record.
        Delta must be 0, layout remains identical, and template row is populated directly.
        """
        if scan_sheet is None or expand_loop_row is None:
            self.fail("services/ engine modules are not yet implemented")

        wb = self.load_fixture()
        ws = wb['RFQ']
        scan = scan_sheet(ws)
        self.assertIn(19, scan.loop_rows)

        delta = expand_loop_row(ws, loop_row=19, count=1, policy='keep_blank')
        self.assertEqual(delta, 0)

        # Total row and formula unchanged
        self.assertEqual(ws['H20'].value, 'Total')
        self.assertEqual(ws['I20'].value, '=SUM(I19:I19)')

        # Original merge preserved
        merged_str = [str(r) for r in ws.merged_cells.ranges]
        self.assertIn('A19:C19', merged_str)

    def test_n_equals_3_matches_specification(self):
        """
        Standard Multi-Row Expansion N = 3 (Section 7.2 Standard):
        Delta = +2. Loop rows duplicate to rows 19, 20, 21.
        Downstream rows shifted by +2. Formulas translated and expanded.
        Conditional formatting and row heights preserved.
        """
        if scan_sheet is None or expand_loop_row is None or fill_loop_rows is None:
            self.fail("services/ engine modules are not yet implemented")

        wb = self.load_fixture()
        ws = wb['RFQ']
        scan = scan_sheet(ws)
        self.assertIn(19, scan.loop_rows)
        loop_row = scan.loop_rows[19]

        row_data_list = [
            {'product': 'Product 1', 'order_number': 'ORD-1', 'design': 'D1', 'quantity': 10, 'uom': 'Pcs', 'price': 100},
            {'product': 'Product 2', 'order_number': 'ORD-2', 'design': 'D2', 'quantity': 20, 'uom': 'Pcs', 'price': 200},
            {'product': 'Product 3', 'order_number': 'ORD-3', 'design': 'D3', 'quantity': 30, 'uom': 'Pcs', 'price': 300},
        ]

        delta = expand_loop_row(ws, loop_row=19, count=3, policy='keep_blank')
        self.assertEqual(delta, 2)

        meta_merges = [(19, 1, 19, 3)]
        fill_loop_rows(ws, loop_row=19, count=3, row_data_list=row_data_list, meta_merges=meta_merges)

        # 1. Preserved values
        self.assertEqual(ws['A19'].value, 'Product 1')
        self.assertEqual(ws['A20'].value, 'Product 2')
        self.assertEqual(ws['A21'].value, 'Product 3')

        # 2. Relative formula translation
        self.assertEqual(ws['I19'].value, '=F19*H19')
        self.assertEqual(ws['I20'].value, '=F20*H20')
        self.assertEqual(ws['I21'].value, '=F21*H21')

        # 3. Cloned merges
        merged_ranges = [str(r) for r in ws.merged_cells.ranges]
        self.assertIn('A19:C19', merged_ranges)
        self.assertIn('A20:C20', merged_ranges)
        self.assertIn('A21:C21', merged_ranges)

        # 4. Shifted summary row & formula range boundary expansion
        self.assertEqual(ws['H22'].value, 'Total')
        self.assertEqual(ws['I22'].value, '=SUM(I19:I21)')

        # 5. Downstream merges shifted (+2)
        self.assertIn('A24:I25', merged_ranges)
        self.assertEqual(ws['A24'].value, 'Notes')
        self.assertIn('A26:I39', merged_ranges)
        self.assertIn('A40:I53', merged_ranges)
        self.assertEqual(ws['A54'].value, 'Signatures')
        self.assertEqual(ws['B56'].value, '${fields.date_order}')

        # 6. Conditional formatting ranges shifted/expanded
        cf_ranges = [str(k.sqref) for k in ws.conditional_formatting._cf_rules.keys()]
        self.assertIn('G19:I22', cf_ranges)
        self.assertIn('G24:I39', cf_ranges)
        self.assertIn('G54:I107', cf_ranges)
        self.assertIn('H23:I23', cf_ranges)
        self.assertIn('G40:I53', cf_ranges)

        # 7. Row heights preserved
        self.assertAlmostEqual(ws.row_dimensions[19].height, 35.45, places=2)
        self.assertAlmostEqual(ws.row_dimensions[20].height, 35.45, places=2)
        self.assertAlmostEqual(ws.row_dimensions[21].height, 35.45, places=2)
        self.assertAlmostEqual(ws.row_dimensions[26].height, 24.0, places=2)

        # 8. Top border style preserved across merged cells (master and slave cells)
        self.assertIsNotNone(ws['A20'].border.top.style)
        self.assertIsNotNone(ws['B20'].border.top.style)
        self.assertIsNotNone(ws['C20'].border.top.style)
        self.assertIsNotNone(ws['A21'].border.top.style)

    def test_n_equals_0_policy_remove(self):
        """
        Edge Case N = 0 with policy 'remove':
        Template row is deleted (delta = -1). Downstream rows shift UP by -1.
        Total row moves up to row 19 (H19 = 'Total'). Downstream merge A22:I23 shifts to A21:I22.
        """
        if expand_loop_row is None:
            self.fail("services/ layout module is not yet implemented")

        wb = self.load_fixture()
        ws = wb['RFQ']
        delta = expand_loop_row(ws, loop_row=19, count=0, policy='remove')
        self.assertEqual(delta, -1)

        # Total row moved to row 19
        self.assertEqual(ws['H19'].value, 'Total')

        # Notes block shifted up by -1: A22:I23 -> A21:I22
        merged_ranges = [str(r) for r in ws.merged_cells.ranges]
        self.assertIn('A21:I22', merged_ranges)

    def test_n_equals_0_policy_keep_blank(self):
        """
        Edge Case N = 0 with policy 'keep_blank':
        Template row is preserved as a blank row (delta = 0).
        Total row remains at row 20 (H20 = 'Total'). Placeholder cleared to empty string.
        """
        if expand_loop_row is None or fill_loop_rows is None:
            self.fail("services/ layout module is not yet implemented")

        wb = self.load_fixture()
        ws = wb['RFQ']
        delta = expand_loop_row(ws, loop_row=19, count=0, policy='keep_blank')
        self.assertEqual(delta, 0)

        meta_merges = [(19, 1, 19, 3)]
        fill_loop_rows(ws, loop_row=19, count=0, row_data_list=[], meta_merges=meta_merges)

        # Placeholder cleared
        self.assertEqual(ws['A19'].value, '')
        # Total row remains at row 20
        self.assertEqual(ws['H20'].value, 'Total')

    def test_n_equals_200_large_batch(self):
        """
        Stress Test N = 200:
        Expands 200 rows (delta = +199).
        Summary formula expands to =SUM(I19:I218).
        Total row shifts to row 219 (H219 = 'Total').
        Verifies all merges intact and execution time < 1.0s.
        """
        if expand_loop_row is None or fill_loop_rows is None:
            self.fail("services/ layout module is not yet implemented")

        wb = self.load_fixture()
        ws = wb['RFQ']

        row_data_list = [
            {
                'product': f'Product {i}',
                'order_number': f'ORD-{i}',
                'design': f'D{i}',
                'quantity': 10.0,
                'uom': 'Pcs',
                'price': 10.0,
            }
            for i in range(1, 201)
        ]

        t0 = time.time()
        delta = expand_loop_row(ws, loop_row=19, count=200, policy='keep_blank')
        self.assertEqual(delta, 199)

        meta_merges = [(19, 1, 19, 3)]
        fill_loop_rows(ws, loop_row=19, count=200, row_data_list=row_data_list, meta_merges=meta_merges)
        elapsed = time.time() - t0

        # Performance constraint: execution under 1.0s
        self.assertLess(elapsed, 1.0, f"Stress expansion took {elapsed:.3f}s, expected < 1.0s")

        # Verify summary row and expanded formula
        self.assertEqual(ws['H219'].value, 'Total')
        self.assertEqual(ws['I219'].value, '=SUM(I19:I218)')

        # Verify last data row content
        self.assertEqual(ws['A218'].value, 'Product 200')

        # Verify loop row merges exist across rows 19 to 218
        merged_ranges = [str(r) for r in ws.merged_cells.ranges]
        self.assertIn('A19:C19', merged_ranges)
        self.assertIn('A218:C218', merged_ranges)
        # 200 cloned row merges + 3 downstream merges = 203 merges minimum in test fixture
        self.assertGreaterEqual(len(merged_ranges), 203)

    def test_html_normalization_single_paragraph(self):
        """Single paragraph HTML is stripped to clean plaintext."""
        html_input = "<p>Text</p>"
        self.assertTrue(is_html(html_input))
        self.assertEqual(to_cell_value(html_input), "Text")

    def test_html_normalization_multiline(self):
        """Multiple paragraphs are converted into lines separated by \n."""
        html_input = "<p>Line 1</p><p>Line 2</p>"
        self.assertTrue(is_html(html_input))
        self.assertEqual(to_cell_value(html_input), "Line 1\nLine 2")

    def test_html_normalization_lists(self):
        """Unordered and ordered list items convert to lines separated by \n."""
        html_input = "<ul><li>A</li><li>B</li></ul>"
        self.assertTrue(is_html(html_input))
        self.assertEqual(to_cell_value(html_input), "A\nB")

    def test_html_normalization_breaks(self):
        """<br>, <br/>, <br /> tags convert to \n."""
        html_input = "Line 1<br/>Line 2<br>Line 3"
        self.assertTrue(is_html(html_input))
        self.assertEqual(to_cell_value(html_input), "Line 1\nLine 2\nLine 3")

    def test_html_normalization_entities(self):
        """HTML entities &amp;, &nbsp;, &lt;, &gt; are unescaped and &nbsp; converted to standard space."""
        html_input = "<p>Hello&nbsp;world &amp; &lt;friends&gt;</p>"
        self.assertTrue(is_html(html_input))
        self.assertEqual(to_cell_value(html_input), "Hello world & <friends>")

    def test_html_normalization_empty(self):
        """Empty HTML or tags containing only whitespace/breaks collapse to empty string."""
        self.assertEqual(to_cell_value("<p><br></p>"), "")
        self.assertEqual(to_cell_value("<p></p>"), "")

    def test_plain_text_preserved(self):
        """Strings without HTML tags are preserved without modification."""
        plain = "1 < 2 and 4 > 3"
        self.assertFalse(is_html(plain))
        self.assertEqual(to_cell_value(plain), "1 < 2 and 4 > 3")

    def test_cell_multiline_wrap_text(self):
        """Ensure ensure_cell_wrap_text sets wrap_text=True without StyleProxy immutability error."""
        wb = openpyxl.Workbook()
        ws = wb.active
        cell = ws['A1']
        multiline_val = to_cell_value("<p>Line 1</p><p>Line 2</p>")
        cell.value = multiline_val
        self.assertIn("\n", cell.value)
        ensure_cell_wrap_text(cell)
        self.assertIsNotNone(cell.alignment)
        self.assertTrue(cell.alignment.wrap_text)

    def test_fill_loop_rows_with_multiline_text(self):
        """Test fill_loop_rows sets wrap_text=True on multiline column cells."""
        wb = self.load_fixture()
        ws = wb['RFQ']
        row_data = [{'product': '<p>Line 1</p><p>Line 2</p>'}]
        expand_loop_row(ws, loop_row=19, count=1, policy='keep_blank')
        fill_loop_rows(ws, loop_row=19, count=1, row_data_list=row_data)
        self.assertEqual(ws['A19'].value, "Line 1\nLine 2")
        self.assertIsNotNone(ws['A19'].alignment)
        self.assertTrue(ws['A19'].alignment.wrap_text)

    def test_evaluator_context_helpers(self):
        """Verify built-in helpers (format_datetime, format_date, html2plaintext) in evaluator context."""
        import datetime
        ctx = build_eval_context(record={})
        self.assertIn("format_date", ctx)
        self.assertIn("format_datetime", ctx)
        self.assertIn("html2plaintext", ctx)
        self.assertIn("to_cell_value", ctx)
        self.assertIn("resolve_path", ctx)

        # Test format_datetime helper
        dt = datetime.datetime(2026, 10, 20, 15, 30, 45)
        self.assertEqual(ctx["format_datetime"](dt), "2026-10-20 15:30:45")
        self.assertEqual(ctx["format_datetime"](dt, "%d/%m/%Y"), "20/10/2026")

        # Test html2plaintext helper
        self.assertEqual(ctx["html2plaintext"]("<p>Line 1</p><p>Line 2</p>"), "Line 1\nLine 2")

    def test_render_with_python_code_mode(self):
        """Verify render_template using mock template in config_mode='code' populating tables & variables."""
        class MockTemplate:
            config_mode = 'code'
            empty_table_policy = 'keep_blank'

            def _execute_python_request(self, record=None, records=None):
                return {
                    'variables': {
                        'tax_included': 'TAX_INCLUDED_YES',
                    },
                    'tables': {
                        'summary': [
                            {'product': 'Product Alpha', 'quantity': 5, 'price': 100.0},
                            {'product': 'Product Beta', 'quantity': 10, 'price': 250.0},
                        ]
                    }
                }

        with open(FIXTURE_PATH, 'rb') as f:
            wb_bytes = f.read()
        rendered_bytes = render_template(wb_bytes, record={}, template=MockTemplate())
        self.assertTrue(len(rendered_bytes) > 0)

        wb_res = openpyxl.load_workbook(io.BytesIO(rendered_bytes))
        ws = wb_res['RFQ']

        # Loop row 19 should be expanded into 2 rows: 19 and 20
        self.assertEqual(ws['A19'].value, 'Product Alpha')
        self.assertEqual(ws['A20'].value, 'Product Beta')
        self.assertEqual(ws['F19'].value, 5)
        self.assertEqual(ws['F20'].value, 10)


if __name__ == '__main__':
    unittest.main()
