import base64
import io
import posixpath
import re
import zipfile

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError

XLSX_MIMETYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
XLSX_MIMETYPES = {
    XLSX_MIMETYPE,
    'application/vnd.ms-excel.sheet.macroEnabled.12',
}
EXCEL_EXTENSIONS = ('.xlsx', '.xlsm')
IMAGE_EXT_TO_MIME = {
    'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'gif': 'image/gif', 'webp': 'image/webp', 'bmp': 'image/bmp',
}

DEFAULT_MAX_FILE_MB = 20
MAX_UNCOMPRESSED_FACTOR = 10   # Zip bomb protection: uncompressed size <= 10x max file size
MAX_ZIP_ENTRIES = 5000


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _excel_editor_max_bytes(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'dn_attachment_excel_editor.max_file_mb'
        ) or self.env['ir.config_parameter'].sudo().get_param(
            'attachment_excel_editor.max_file_mb', DEFAULT_MAX_FILE_MB
        )
        try:
            return int(float(param) * 1024 * 1024)
        except (TypeError, ValueError):
            return DEFAULT_MAX_FILE_MB * 1024 * 1024

    def _excel_editor_check(self, operation):
        self.ensure_one()
        if not self.exists():
            raise UserError(_("Attachment does not exist or has been deleted."))
        try:
            self.check_access(operation)
        except AccessError:
            raise AccessError(
                _("You do not have permission to modify this file.") if operation == 'write'
                else _("You do not have permission to view this file.")
            )
        if self.type != 'binary':
            raise UserError(_("Only binary attachments are supported."))
        name = (self.name or '').lower()
        if not (name.endswith(EXCEL_EXTENSIONS) or self.mimetype in XLSX_MIMETYPES):
            raise UserError(_("Only .xlsx / .xlsm files are supported."))

    def _excel_editor_can_write(self):
        self.ensure_one()
        try:
            self.check_access('write')
            return True
        except AccessError:
            return False

    def _excel_editor_get_next_version_name(self):
        """Derive the next version name (e.g. 'report (v2).xlsx')."""
        original_name = self.name or 'spreadsheet.xlsx'
        base, _ext = posixpath.splitext(original_name)
        ext = '.xlsx'

        match = re.search(r'^(.*?)\s+\(v(\d+)\)$', base)
        if match:
            root_name = match.group(1)
            current_v = int(match.group(2))
        else:
            root_name = base
            current_v = 1

        target_v = current_v + 1
        if self.res_model and self.res_id:
            domain = [
                ('res_model', '=', self.res_model),
                ('res_id', '=', self.res_id),
                ('name', '=like', f"{root_name} (v%){ext}"),
            ]
            existing_names = set(self.env['ir.attachment'].search(domain).mapped('name'))
            while f"{root_name} (v{target_v}){ext}" in existing_names:
                target_v += 1

        return f"{root_name} (v{target_v}){ext}"

    def _excel_editor_link_host_m2m(self, new_attachment):
        """Link new_attachment to any many2many field on host record pointing to self."""
        if not (self.res_model and self.res_id and self.res_model in self.env):
            return
        try:
            host_record = self.env[self.res_model].browse(self.res_id).exists()
            if not host_record:
                return
            for field_name, field in host_record._fields.items():
                if field.type == 'many2many' and field.comodel_name == 'ir.attachment':
                    try:
                        if self in host_record[field_name]:
                            host_record.write({field_name: [fields.Command.link(new_attachment.id)]})
                    except Exception:
                        continue
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public ORM API
    # ------------------------------------------------------------------
    def excel_editor_load(self):
        """Extract xlsx archive into dict {path: content} for o-spreadsheet load().

        - .xml/.rels files -> text string
        - Images in xl/media -> {"imageSrc": "data:image/...;base64,..."}
        - Everything else (vbaProject.bin, etc.) is ignored => VBA macros stripped.
        """
        self.ensure_one()
        self._excel_editor_check('read')
        raw = base64.b64decode(self.datas or b'')
        if not raw:
            raise UserError(_("Attachment file is empty."))
        max_bytes = self._excel_editor_max_bytes()
        if len(raw) > max_bytes:
            raise UserError(_("File is too large (maximum %s MB).", max_bytes // 1024 // 1024))

        files = {}
        has_macro = False
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                infos = zf.infolist()
                if len(infos) > MAX_ZIP_ENTRIES:
                    raise UserError(_("The xlsx file has too many entries."))
                if sum(i.file_size for i in infos) > max_bytes * MAX_UNCOMPRESSED_FACTOR:
                    raise UserError(_("Uncompressed file content is too large."))
                for info in infos:
                    if info.is_dir():
                        continue
                    path = posixpath.normpath(info.filename)
                    if path.startswith(('/', '..')):
                        continue
                    lower = path.lower()
                    if lower.endswith('vbaproject.bin'):
                        has_macro = True
                        continue
                    if lower.endswith('.rels'):
                        files[path] = self._excel_editor_relativize_rels(
                            path, zf.read(info).decode('utf-8-sig'))
                    elif lower.endswith('.xml'):
                        xml_content = zf.read(info).decode('utf-8-sig')
                        if lower == '[content_types].xml' or path == '[Content_Types].xml':
                            path = '[Content_Types].xml'
                            xml_content = re.sub(
                                r'(\bPartName\s*=\s*["\'])([^"\']+)(["\'])',
                                lambda m: m.group(1) + m.group(2).replace('\\', '/') + m.group(3),
                                xml_content,
                            )
                        elif lower.startswith('xl/worksheets/') or '<col' in xml_content:
                            xml_content = self._excel_editor_sanitize_worksheet_xml(xml_content)
                        elif 'chart' in lower or '<c:chart' in xml_content:
                            xml_content = self._excel_editor_sanitize_chart_xml(xml_content)
                        files[path] = xml_content
                    elif lower.startswith('xl/media/'):
                        mime = IMAGE_EXT_TO_MIME.get(lower.rsplit('.', 1)[-1])
                        if mime:
                            b64 = base64.b64encode(zf.read(info)).decode()
                            files[path] = {'imageSrc': f'data:{mime};base64,{b64}'}
        except zipfile.BadZipFile:
            raise UserError(_("The file is not a valid xlsx archive (it may be corrupted or password-protected)."))

        if '[Content_Types].xml' not in files:
            raise UserError(_("Invalid xlsx file: missing [Content_Types].xml."))

        return {
            'id': self.id,
            'name': self.name,
            'files': files,
            'has_macro': has_macro or (self.name or '').lower().endswith('.xlsm'),
            'write_date': self.write_date and self.write_date.isoformat(),
            'can_write': self._excel_editor_can_write(),
            'save_option': self.env.user.excel_editor_save_option or 'ask',
        }

    def excel_editor_save(self, files, write_date=None, save_mode='overwrite', remember_choice=False):
        """Package exported files from model.exportXLSX() into xlsx archive and save.

        :param files: list[{'path', 'content'} | {'path', 'imageSrc': 'data:...'}]
        :param write_date: ISO write_date when opened, used for concurrency conflict detection
        :param save_mode: 'overwrite' or 'new_version'
        :param remember_choice: if True, persist save_mode to user preferences
        """
        self.ensure_one()
        self._excel_editor_check('write')
        if write_date and self.write_date and self.write_date.isoformat() != write_date:
            raise UserError(_(
                "The file has been modified by someone else since you opened it. "
                "Please download your changes and reload the record."
            ))

        if remember_choice and save_mode in ('overwrite', 'new_version'):
            self.env.user.excel_editor_save_option = save_mode

        content = self._excel_editor_build_xlsx(files)
        if len(content) > self._excel_editor_max_bytes():
            raise UserError(_("Saved file exceeds allowed size limit."))

        if save_mode == 'new_version':
            next_name = self._excel_editor_get_next_version_name()
            vals = {
                'name': next_name,
                'raw': content,
                'mimetype': XLSX_MIMETYPE,
                'res_model': self.res_model,
                'res_id': self.res_id,
                'type': 'binary',
            }
            new_att = self.env['ir.attachment'].create(vals)
            self._excel_editor_link_host_m2m(new_att)
            return {
                'id': new_att.id,
                'name': new_att.name,
                'mimetype': new_att.mimetype,
                'write_date': new_att.write_date and new_att.write_date.isoformat(),
                'is_new': True,
            }

        # 'overwrite' mode
        vals = {'raw': content, 'mimetype': XLSX_MIMETYPE}
        name = self.name or 'spreadsheet.xlsx'
        if name.lower().endswith('.xlsm'):
            vals['name'] = name[:-5] + '.xlsx'
        self.write(vals)
        return {
            'id': self.id,
            'name': self.name,
            'mimetype': self.mimetype,
            'write_date': self.write_date and self.write_date.isoformat(),
            'is_new': False,
        }

    def excel_editor_export(self, files):
        """Package current spreadsheet for download without saving to attachment."""
        self.ensure_one()
        self._excel_editor_check('read')
        content = self._excel_editor_build_xlsx(files)
        name = self.name or 'spreadsheet.xlsx'
        if not name.lower().endswith('.xlsx'):
            name = (name[:-5] if name.lower().endswith('.xlsm') else name) + '.xlsx'
        return {'name': name, 'data': base64.b64encode(content).decode()}

    def _excel_editor_build_xlsx(self, files):
        if not files or not isinstance(files, list):
            raise UserError(_("No data to save."))
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Put [Content_Types].xml first for optimal Excel compatibility
            valid_files = [f for f in files if isinstance(f, dict)]
            ordered = sorted(valid_files, key=lambda f: f.get('path') != '[Content_Types].xml')
            for f in ordered:
                path = posixpath.normpath(str(f.get('path') or ''))
                if not path or path == '.' or path.startswith(('/', '..')):
                    raise UserError(_("Invalid file path in spreadsheet archive."))
                if 'imageSrc' in f:
                    data = self._excel_editor_decode_data_url(f['imageSrc'])
                    if data is None:
                        continue  # External image url -> skip
                    zf.writestr(path, data)
                else:
                    content = f.get('content') or ''
                    path_lower = path.lower()
                    if path_lower.endswith('.xml'):
                        if path_lower == '[content_types].xml' or path == '[Content_Types].xml':
                            path = '[Content_Types].xml'
                            content = re.sub(
                                r'(\bPartName\s*=\s*["\'])([^"\']+)(["\'])',
                                lambda m: m.group(1) + m.group(2).replace('\\', '/') + m.group(3),
                                content,
                            )
                        elif path_lower.startswith('xl/worksheets/') or '<col' in content:
                            content = self._excel_editor_sanitize_worksheet_xml(content)
                        elif 'chart' in path_lower or '<c:chart' in content:
                            content = self._excel_editor_sanitize_chart_xml(content)
                    zf.writestr(path, content.encode('utf-8'))
        return buffer.getvalue()

    _REL_TAG_RE = re.compile(r'<Relationship\b[^>]*>', re.I)
    _REL_TARGET_RE = re.compile(r'(\bTarget\s*=\s*)(["\'])(/[^"\']*)\2')
    _COL_TAG_RE = re.compile(r'<col\b([^>]*)/?>', re.I)
    _ATTR_MIN_RE = re.compile(r'(\bmin\s*=\s*)(["\'])(.*?)\2', re.I)
    _ATTR_MAX_RE = re.compile(r'(\bmax\s*=\s*)(["\'])(.*?)\2', re.I)
    _CHART_F_TAG_RE = re.compile(r'<c:f>([^<]+)</c:f>', re.I)
    _CHART_RANGE_RE = re.compile(
        r"^(?P<sheet>(?:'[^']+'|[^!]+)!)?"
        r"(?P<c1_fix>\$?)(?P<c1>[A-Za-z]+)(?P<r1_fix>\$?)(?P<r1>\d+):"
        r"(?P<c2_fix>\$?)(?P<c2>[A-Za-z]+)(?P<r2_fix>\$?)(?P<r2>\d+)$"
    )

    @classmethod
    def _excel_editor_sanitize_chart_xml(cls, text):
        """Sanitize chart XML to prevent negative column/row indexing on import.

        When a chart series has a title reference (<c:tx>...<c:f>), o-spreadsheet's
        convertExcelRangeToSheetXC considers dataSetsHaveTitle=True. If height=1, it
        decrements zone.left by 1 (e.g. 0 -> -1); if width=1, it decrements zone.top
        by 1 (e.g. 0 -> -1). Decrementing 0 to -1 throws:
        'Could not parse Excel spreadsheet: number must be positive. Got -1'.

        Sanitizing ranges that start at column A (height=1) to column B, or row 1
        (width=1) to row 2 allows o-spreadsheet to decrement back to A / 1 safely,
        reconstructing the intended original range.
        """
        if not isinstance(text, str) or '<c:chart' not in text:
            return text
        if not re.search(r'<c:tx\b[\s\S]*?<c:f\b', text, re.I):
            return text

        def fix_formula(match):
            formula = match.group(1).strip()
            rm = cls._CHART_RANGE_RE.match(formula)
            if not rm:
                return match.group(0)

            sheet = rm.group('sheet') or ''
            c1_fix = rm.group('c1_fix')
            c1 = rm.group('c1').upper()
            r1_fix = rm.group('r1_fix')
            r1 = int(rm.group('r1'))

            c2_fix = rm.group('c2_fix')
            c2 = rm.group('c2').upper()
            r2_fix = rm.group('r2_fix')
            r2 = int(rm.group('r2'))

            # height === 1: r1 == r2. If c1 == 'A', adjust to 'B'
            if r1 == r2 and c1 == 'A':
                fixed_ref = f"{sheet}{c1_fix}B{r1_fix}{r1}:{c2_fix}{c2}{r2_fix}{r2}"
                return f"<c:f>{fixed_ref}</c:f>"

            # width === 1: c1 == c2. If r1 == 1, adjust to 2
            if c1 == c2 and r1 == 1:
                fixed_ref = f"{sheet}{c1_fix}{c1}{r1_fix}2:{c2_fix}{c2}{r2_fix}{r2}"
                return f"<c:f>{fixed_ref}</c:f>"

            return match.group(0)

        return cls._CHART_F_TAG_RE.sub(fix_formula, text)

    @classmethod
    def _excel_editor_sanitize_worksheet_xml(cls, text):
        """Sanitize worksheet XML to ensure all <col> elements have valid min/max.

        o-spreadsheet's convertCells throws 'number must be positive. Got -1'
        if col.min is 0 or negative. OpenXML standard requires 1-based column indexing.
        """
        if not isinstance(text, str) or '<col' not in text:
            return text

        def fix_col_tag(match):
            tag = match.group(0)
            min_m = cls._ATTR_MIN_RE.search(tag)
            max_m = cls._ATTR_MAX_RE.search(tag)
            if not min_m and not max_m:
                return tag

            min_val = None
            max_val = None
            if min_m:
                try:
                    min_val = int(min_m.group(3).strip())
                except (ValueError, TypeError):
                    min_val = 1
            if max_m:
                try:
                    max_val = int(max_m.group(3).strip())
                except (ValueError, TypeError):
                    max_val = 1

            if min_val is not None and min_val < 1:
                min_val = 1
            if max_val is not None and max_val < 1:
                max_val = min_val if min_val is not None else 1
            if min_val is not None and max_val is not None and max_val < min_val:
                max_val = min_val

            if min_m and min_val is not None:
                tag = cls._ATTR_MIN_RE.sub(
                    lambda m: f'{m.group(1)}{m.group(2)}{min_val}{m.group(2)}', tag, count=1)
            if max_m and max_val is not None:
                tag = cls._ATTR_MAX_RE.sub(
                    lambda m: f'{m.group(1)}{m.group(2)}{max_val}{m.group(2)}', tag, count=1)

            return tag

        return cls._COL_TAG_RE.sub(fix_col_tag, text)

    @classmethod
    def _excel_editor_relativize_rels(cls, rels_path, text):
        """Convert absolute targets (e.g. '/xl/worksheets/sheet1.xml') into relative ones.

        o-spreadsheet's xlsx reader requires relative paths.
        Also normalizes any backslashes in relationship targets.
        """
        rels_dir, _rels_name = posixpath.split(rels_path)
        source_dir = posixpath.dirname(rels_dir)
        start = source_dir or '.'

        def fix_tag(match):
            tag = match.group(0)
            if re.search(r'TargetMode\s*=\s*["\']External', tag, re.I):
                return tag
            # Normalize Windows-style backslashes in targets
            tag = re.sub(
                r'(\bTarget\s*=\s*["\'])([^"\']+)(["\'])',
                lambda m: m.group(1) + m.group(2).replace('\\', '/') + m.group(3),
                tag,
            )
            return cls._REL_TARGET_RE.sub(
                lambda m: '%s%s%s%s' % (
                    m.group(1), m.group(2),
                    posixpath.relpath(m.group(3).lstrip('/'), start), m.group(2)),
                tag)

        return cls._REL_TAG_RE.sub(fix_tag, text)

    @staticmethod
    def _excel_editor_decode_data_url(src):
        if not isinstance(src, str) or not src.startswith('data:') or ';base64,' not in src:
            return None
        try:
            return base64.b64decode(src.split(';base64,', 1)[1])
        except Exception:  # noqa: BLE001
            return None
