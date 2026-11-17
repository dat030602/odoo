import base64
import io
import zipfile
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged


def _make_minimal_xlsx(include_vba=False):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        zf.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
        zf.writestr('xl/workbook.xml', '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>')
        zf.writestr('xl/_rels/workbook.xml.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
        zf.writestr('xl/worksheets/sheet1.xml', '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>')
        if include_vba:
            zf.writestr('xl/vbaProject.bin', b'\x00\x01\x02vba_dummy_macro')
    return buf.getvalue()


@tagged('post_install', '-at_install')
class TestExcelEditor(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.xlsx_data = _make_minimal_xlsx()
        cls.xlsx_b64 = base64.b64encode(cls.xlsx_data)

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner with Excel',
        })

        cls.attachment = cls.env['ir.attachment'].create({
            'name': 'financial_report.xlsx',
            'datas': cls.xlsx_b64,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'res.partner',
            'res_id': cls.partner.id,
            'type': 'binary',
        })
        cls.partner.write({'excel_attachment_ids': [(4, cls.attachment.id)]})

        # Test user
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test Standard User',
            'login': 'test_standard_user',
            'email': 'test_standard_user@example.com',
            'group_ids': [fields.Command.set([cls.env.ref('base.group_user').id])],
        })

    def test_load_preferences_and_file(self):
        """Test default preferences and successful excel_editor_load."""
        self.assertEqual(self.env.user.excel_editor_save_option, 'ask')
        res = self.attachment.excel_editor_load()
        self.assertEqual(res['id'], self.attachment.id)
        self.assertEqual(res['name'], 'financial_report.xlsx')
        self.assertEqual(res['save_option'], 'ask')
        self.assertTrue(res['can_write'])
        self.assertFalse(res['has_macro'])
        self.assertIn('[Content_Types].xml', res['files'])
        self.assertIn('xl/workbook.xml', res['files'])

    def test_save_overwrite(self):
        """Test overwriting original attachment."""
        files = [
            {'path': '[Content_Types].xml', 'content': '<?xml version="1.0"?><Types/>'},
            {'path': 'xl/workbook.xml', 'content': '<?xml version="1.0"?><workbook/>'},
        ]
        res = self.attachment.excel_editor_save(
            files,
            write_date=self.attachment.write_date.isoformat(),
            save_mode='overwrite',
        )
        self.assertFalse(res['is_new'])
        self.assertEqual(res['id'], self.attachment.id)
        self.assertEqual(res['name'], 'financial_report.xlsx')

    def test_save_new_version_naming_and_linking(self):
        """Test creating a new version: check v2 and v3 auto-increment naming and host m2m linking."""
        files = [
            {'path': '[Content_Types].xml', 'content': '<?xml version="1.0"?><Types/>'},
            {'path': 'xl/workbook.xml', 'content': '<?xml version="1.0"?><workbook/>'},
        ]
        # First save with new_version -> should create (v2)
        res_v2 = self.attachment.excel_editor_save(
            files,
            write_date=self.attachment.write_date.isoformat(),
            save_mode='new_version',
        )
        self.assertTrue(res_v2['is_new'])
        self.assertNotEqual(res_v2['id'], self.attachment.id)
        self.assertEqual(res_v2['name'], 'financial_report (v2).xlsx')

        # Check partner host record m2m field contains both attachments
        self.assertIn(self.attachment.id, self.partner.excel_attachment_ids.ids)
        self.assertIn(res_v2['id'], self.partner.excel_attachment_ids.ids)

        # Save again from v2 with new_version -> should create (v3)
        att_v2 = self.env['ir.attachment'].browse(res_v2['id'])
        res_v3 = att_v2.excel_editor_save(
            files,
            write_date=att_v2.write_date.isoformat(),
            save_mode='new_version',
        )
        self.assertTrue(res_v3['is_new'])
        self.assertEqual(res_v3['name'], 'financial_report (v3).xlsx')
        self.assertIn(res_v3['id'], self.partner.excel_attachment_ids.ids)

    def test_save_remember_choice(self):
        """Test remember_choice updates user's excel_editor_save_option."""
        self.env.user.excel_editor_save_option = 'ask'
        files = [
            {'path': '[Content_Types].xml', 'content': '<?xml version="1.0"?><Types/>'},
        ]
        self.attachment.excel_editor_save(
            files,
            write_date=self.attachment.write_date.isoformat(),
            save_mode='new_version',
            remember_choice=True,
        )
        self.assertEqual(self.env.user.excel_editor_save_option, 'new_version')

    def test_save_concurrency_conflict(self):
        """Test that passing an outdated write_date raises UserError."""
        files = [
            {'path': '[Content_Types].xml', 'content': '<?xml version="1.0"?><Types/>'},
        ]
        with self.assertRaises(UserError):
            self.attachment.excel_editor_save(
                files,
                write_date='2020-01-01T00:00:00',
                save_mode='overwrite',
            )

    def test_load_xlsm_macro_stripped(self):
        """Test that .xlsm files have VBA macros stripped and has_macro flag set."""
        xlsm_data = _make_minimal_xlsx(include_vba=True)
        xlsm_att = self.env['ir.attachment'].create({
            'name': 'macro_enabled.xlsm',
            'datas': base64.b64encode(xlsm_data),
            'mimetype': 'application/vnd.ms-excel.sheet.macroEnabled.12',
            'res_model': 'res.partner',
            'res_id': self.partner.id,
            'type': 'binary',
        })
        res = xlsm_att.excel_editor_load()
        self.assertTrue(res['has_macro'])
        self.assertNotIn('xl/vbaProject.bin', res['files'])

        # Saving xlsm should rename extension to .xlsx
        save_res = xlsm_att.excel_editor_save(
            [{'path': '[Content_Types].xml', 'content': '<?xml version="1.0"?><Types/>'}],
            save_mode='overwrite',
        )
        self.assertTrue(save_res['name'].endswith('.xlsx'))

    def test_security_access_rights(self):
        """Test read and write permissions enforcement."""
        # Admin can write
        self.assertTrue(self.attachment._excel_editor_can_write())

        # Test non-binary attachment check
        url_att = self.env['ir.attachment'].create({
            'name': 'url_link.xlsx',
            'type': 'url',
            'url': 'https://example.com/test.xlsx',
        })
        with self.assertRaises(UserError):
            url_att.excel_editor_load()

    def test_security_multi_user(self):
        """Test multi-user security: read access, restricted write access, and user preferences."""
        # 1. Standard user can load attachment when having read access
        user_att = self.attachment.with_user(self.test_user)
        res = user_att.excel_editor_load()
        self.assertEqual(res['id'], self.attachment.id)
        self.assertEqual(res['name'], 'financial_report.xlsx')

        # 2. When user lacks write access, _excel_editor_can_write() is False and excel_editor_save() raises AccessError
        def _deny_write(operation):
            if operation == 'write':
                raise AccessError("Access Denied")

        with patch.object(type(self.attachment), 'check_access', side_effect=_deny_write):
            self.assertFalse(user_att._excel_editor_can_write())
            with self.assertRaises(AccessError):
                user_att.excel_editor_save(
                    [{'path': '[Content_Types].xml', 'content': '<?xml version="1.0"?><Types/>'}],
                    save_mode='overwrite',
                )

        # 3. Standard users can read and write their own excel_editor_save_option preference in res.users
        user_rec = self.env['res.users'].with_user(self.test_user).browse(self.test_user.id)
        self.assertEqual(user_rec.excel_editor_save_option, 'ask')
        user_rec.write({'excel_editor_save_option': 'new_version'})
        self.assertEqual(user_rec.excel_editor_save_option, 'new_version')

    def test_corrupt_and_zip_bomb_protections(self):
        """Test protection against corrupt files and invalid zip structures."""
        # Corrupt archive
        corrupt_att = self.env['ir.attachment'].create({
            'name': 'corrupted.xlsx',
            'datas': base64.b64encode(b'NOT A REAL ZIP FILE CONTENT'),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'type': 'binary',
        })
        with self.assertRaises(UserError):
            corrupt_att.excel_editor_load()

        # Missing [Content_Types].xml
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('dummy.txt', 'hello')
        missing_content_att = self.env['ir.attachment'].create({
            'name': 'missing_content.xlsx',
            'datas': base64.b64encode(buf.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'type': 'binary',
        })
        with self.assertRaises(UserError):
            missing_content_att.excel_editor_load()

        # Invalid file path in build_xlsx (path traversal attempt)
        bad_files = [{'path': '../../etc/passwd', 'content': 'malicious'}]
        with self.assertRaises(UserError):
            self.attachment._excel_editor_build_xlsx(bad_files)

    def test_load_sanitizes_corrupt_col_min_zero(self):
        """Test that excel_editor_load normalizes <col min="0" ...> and negative col indexes to min="1"."""
        buf = io.BytesIO()
        corrupt_sheet = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<cols>'
            '<col min="0" max="0" width="10" style="1"/>'
            '<col min="-1" max="-1" width="12"/>'
            '<col min="0" max="5" customWidth="1"/>'
            '<col min="4" max="2"/>'
            '<col min="2" max="3" width="8"/>'
            '</cols>'
            '</worksheet>'
        )
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
            zf.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
            zf.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>')
            zf.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
            zf.writestr('xl/worksheets/sheet1.xml', corrupt_sheet)

        att = self.env['ir.attachment'].create({
            'name': 'corrupted_cols.xlsx',
            'datas': base64.b64encode(buf.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'res.partner',
            'res_id': self.partner.id,
            'type': 'binary',
        })
        res = att.excel_editor_load()
        loaded_xml = res['files']['xl/worksheets/sheet1.xml']
        self.assertNotIn('min="0"', loaded_xml)
        self.assertNotIn('max="0"', loaded_xml)
        self.assertNotIn('min="-1"', loaded_xml)
        self.assertNotIn('max="-1"', loaded_xml)
        self.assertIn('min="1" max="1" width="10" style="1"', loaded_xml)
        self.assertIn('min="1" max="1" width="12"', loaded_xml)
        self.assertIn('min="1" max="5"', loaded_xml)
        self.assertIn('min="4" max="4"', loaded_xml)
        self.assertIn('min="2" max="3"', loaded_xml)

    def test_save_sanitizes_corrupt_col_min_zero(self):
        """Test that excel_editor_save normalizes <col min="0" ...> before writing into xlsx archive."""
        corrupt_sheet = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<cols>'
            '<col min="0" max="0" width="15" style="2"/>'
            '</cols>'
            '</worksheet>'
        )
        files = [
            {'path': '[Content_Types].xml', 'content': '<?xml version="1.0"?><Types/>'},
            {'path': 'xl/workbook.xml', 'content': '<?xml version="1.0"?><workbook/>'},
            {'path': 'xl/worksheets/sheet1.xml', 'content': corrupt_sheet},
        ]
        res = self.attachment.excel_editor_save(
            files,
            write_date=self.attachment.write_date.isoformat(),
            save_mode='overwrite',
        )
        self.assertFalse(res['is_new'])
        # Re-load attachment and inspect stored zip
        reloaded = self.attachment.excel_editor_load()
        sheet_xml = reloaded['files']['xl/worksheets/sheet1.xml']
        self.assertNotIn('min="0"', sheet_xml)
        self.assertNotIn('max="0"', sheet_xml)
        self.assertIn('min="1" max="1"', sheet_xml)

    def test_rels_relativization_and_normalization(self):
        """Test that .rels files have absolute targets relativized and backslashes normalized."""
        rels_content = (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="/xl/worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Target="worksheets\\sheet2.xml"/>'
            '<Relationship Id="rId3" Target="http://example.com" TargetMode="External"/>'
            '</Relationships>'
        )
        normalized = self.attachment._excel_editor_relativize_rels('xl/_rels/workbook.xml.rels', rels_content)
        self.assertIn('Target="worksheets/sheet1.xml"', normalized)
        self.assertIn('Target="worksheets/sheet2.xml"', normalized)
        self.assertIn('Target="http://example.com"', normalized)

    def test_content_types_normalization(self):
        """Test that [Content_Types].xml PartName backslashes are normalized to forward slashes."""
        ct_content = (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="\\xl\\worksheets\\sheet1.xml" ContentType="sheet"/>'
            '</Types>'
        )
        files = [
            {'path': '[Content_Types].xml', 'content': ct_content},
            {'path': 'xl/workbook.xml', 'content': '<?xml version="1.0"?><workbook/>'},
        ]
        self.attachment.excel_editor_save(
            files,
            write_date=self.attachment.write_date.isoformat(),
            save_mode='overwrite',
        )
        reloaded = self.attachment.excel_editor_load()
        ct_loaded = reloaded['files']['[Content_Types].xml']
        self.assertNotIn('\\xl\\worksheets', ct_loaded)
        self.assertIn('PartName="/xl/worksheets/sheet1.xml"', ct_loaded)

    def test_chart_xml_sanitization_negative_index_prevention(self):
        """Test that chart*.xml category ranges starting at column A (row1==row2)
        or row 1 (col1==col2) with series title references are adjusted so
        o-spreadsheet's convertExcelRangeToSheetXC does not compute negative index -1.
        """
        chart_xml = (
            '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">'
            '<c:chart>'
            '<c:plotArea>'
            '<c:barChart>'
            '<c:ser>'
            '<c:tx><c:strRef><c:f>\'Data tổng\'!$B$2</c:f></c:strRef></c:tx>'
            '<c:cat><c:strRef><c:f>\'Data tổng\'!A3:D3</c:f></c:strRef></c:cat>'
            '<c:val><c:numRef><c:f>\'Data tổng\'!$A$1:$A$10</c:f></c:numRef></c:val>'
            '</c:ser>'
            '</c:barChart>'
            '</c:plotArea>'
            '</c:chart>'
            '</c:chartSpace>'
        )
        # Test classmethod directly
        sanitized = self.attachment._excel_editor_sanitize_chart_xml(chart_xml)
        self.assertIn("<c:f>'Data tổng'!B3:D3</c:f>", sanitized)
        self.assertIn("<c:f>'Data tổng'!$A$2:$A$10</c:f>", sanitized)

        # Test save & reload round-trip through attachment
        files = [
            {'path': '[Content_Types].xml', 'content': '<?xml version="1.0"?><Types/>'},
            {'path': 'xl/workbook.xml', 'content': '<?xml version="1.0"?><workbook/>'},
            {'path': 'xl/charts/chart1.xml', 'content': chart_xml},
        ]
        self.attachment.excel_editor_save(
            files,
            write_date=self.attachment.write_date.isoformat(),
            save_mode='overwrite',
        )
        reloaded = self.attachment.excel_editor_load()
        saved_chart_xml = reloaded['files']['xl/charts/chart1.xml']
        self.assertIn("<c:f>'Data tổng'!B3:D3</c:f>", saved_chart_xml)
        self.assertIn("<c:f>'Data tổng'!$A$2:$A$10</c:f>", saved_chart_xml)
