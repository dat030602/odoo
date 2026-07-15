# -*- coding: utf-8 -*-
from datetime import datetime, time
import pytz

import xlsxwriter

from odoo import fields, models

TITLE = "BÁO CÁO CHI TIẾT NHẬT KÝ CẬP NHẬT"

COLUMNS = [
    {"size": 6, "name": "STT", "field": "stt", "type": "number_c_int"},
    {
        "size": 18,
        "name": "Thời gian",
        "field": "create_date",
        "type": "datetime",
    },
    {"size": 12, "name": "Loại", "field": "method_label", "type": "text"},
    {"size": 12, "name": "Phân hệ", "field": "model_id", "type": "text"},
    {"size": 12, "name": "ID bản ghi", "field": "res_id", "type": "number_c_int"},
    {"size": 12, "name": "ID người dùng", "field": "user_id", "type": "number_c_int"},
    {"size": 24, "name": "Người dùng", "field": "user_name", "type": "text"},
    {"size": 28, "name": "Trường update", "field": "field_updated", "type": "text"},
    {"size": 35, "name": "Giá trị cũ", "field": "old_value", "type": "text"},
    {"size": 35, "name": "Giá trị mới", "field": "new_value", "type": "text"},
]

METHOD_LABELS = {
    "create": "Thêm",
    "write": "Sửa",
    "unlink": "Xóa",
}

METHOD_ORDER = {
    "create": 1,
    "write": 2,
    "unlink": 3,
}


def format_workbook(workbook, font_size, font_name="Times New Roman", **kwargs):
    cell_format = workbook.add_format()
    cell_format.set_font_name(font_name)
    cell_format.set_font_size(font_size)
    cell_format.set_align("vcenter")

    for key, value in kwargs.items():
        method_name = f"set_{key}"
        if hasattr(cell_format, method_name):
            getattr(cell_format, method_name)(value)
    return cell_format


def create_formats(workbook):
    return {
        "title_main": format_workbook(workbook, 14, bold=True, align="center"),
        "title_sub": format_workbook(workbook, 10, italic=True, align="center"),
        "header": format_workbook(
            workbook, 10, bold=True, border=1, text_wrap=True, align="center"
        ),
        "text": format_workbook(workbook, 10, border=1, text_wrap=True, align="left"),
        "datetime": format_workbook(
            workbook,
            10,
            border=1,
            text_wrap=True,
            align="center",
            num_format="dd/mm/yyyy hh:mm:ss",
        ),
        "number_c_int": format_workbook(
            workbook, 10, border=1, align="center", num_format="#,##0"
        ),
    }


class AuditlogLineXlsx(models.AbstractModel):
    _name = "report.ccv_auditlog_line_report_xlsx.auditlog_line_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Audit Log Line XLSX"

    def _get_user_name(self, user):
        if not user:
            return ""
        return getattr(user, "name_without_user", False) or user.name or ""

    def _get_method_label(self, method):
        return METHOD_LABELS.get(method, method or "")

    def _to_user_datetime(self, dt_value):
        if not dt_value:
            return dt_value
        local_dt = fields.Datetime.context_timestamp(self, dt_value)
        return local_dt.replace(tzinfo=None)

    def _local_date_range_to_utc(self, date_from, date_to):
        user_tz_name = self.env.user.tz or "UTC"
        try:
            user_tz = pytz.timezone(user_tz_name)
        except pytz.UnknownTimeZoneError:
            user_tz = pytz.UTC

        local_dt_from = user_tz.localize(datetime.combine(date_from, time.min))
        local_dt_to = user_tz.localize(datetime.combine(date_to, time.max))
        dt_from = local_dt_from.astimezone(pytz.UTC).replace(tzinfo=None)
        dt_to = local_dt_to.astimezone(pytz.UTC).replace(tzinfo=None)
        return dt_from, dt_to

    def _prepare_data(self, records):
        sorted_records = records.sorted(
            key=lambda r: (
                r.create_date or datetime.min,
                r.model_model or "",
                r.res_id or 0,
                METHOD_ORDER.get(r.method, 99),
                self._get_user_name(r.user_id) or "",
            )
        )

        lines = []
        for index, rec in enumerate(sorted_records, start=1):
            lines.append(
                {
                    "stt": index,
                    "create_date": self._to_user_datetime(rec.create_date),
                    "method_label": self._get_method_label(rec.method),
                    "model_id": rec.model_id.name or "",
                    "res_id": rec.res_id or 0,
                    "user_id": rec.user_id.id or 0,
                    "user_name": self._get_user_name(rec.user_id),
                    "field_updated": rec.field_description or rec.field_name or "",
                    "old_value": rec.old_value_text or rec.old_value or "",
                    "new_value": rec.new_value_text or rec.new_value or "",
                }
            )
        return lines

    def _get_report_records(self, obj):
        dt_from, dt_to = self._local_date_range_to_utc(obj.date_from, obj.date_to)
        return self.env["auditlog.log.line.view"].search([
            ("create_date", ">=", dt_from),
            ("create_date", "<=", dt_to),
        ])

    def _add_title(self, sheet, formats, records, date_from=None, date_to=None):
        last_col = len(COLUMNS) - 1
        sheet.merge_range(1, 0, 1, last_col, TITLE, formats["title_main"])
        if date_from and date_to:
            subtitle = "Từ ngày %s đến ngày %s - Tổng số dòng: %s" % (
                date_from.strftime("%d/%m/%Y"),
                date_to.strftime("%d/%m/%Y"),
                len(records),
            )
        else:
            subtitle = "Tổng số dòng: %s" % len(records)
        sheet.merge_range(2, 0, 2, last_col, subtitle, formats["title_sub"])

    def _add_header(self, sheet, formats):
        row = 4
        for col_idx, col_def in enumerate(COLUMNS):
            sheet.set_column(col_idx, col_idx, col_def["size"])
            sheet.write(row, col_idx, col_def["name"], formats["header"])

    def _add_body(self, sheet, formats, rows):
        start_row = 5
        for row_idx, row_data in enumerate(rows, start=start_row):
            for col_idx, col_def in enumerate(COLUMNS):
                field_name = col_def["field"]
                cell_type = col_def["type"]
                fmt = formats.get(cell_type, formats["text"])
                value = row_data.get(field_name, "")
                if cell_type == "datetime" and value and isinstance(value, datetime):
                    sheet.write_datetime(row_idx, col_idx, value, fmt)
                else:
                    sheet.write(row_idx, col_idx, value, fmt)

    def generate_xlsx_report(self, workbook: xlsxwriter.Workbook, data, records):
        for obj in self.env['ccv.auditlog.line.report.wizard'].browse(records.ids):
            sheet = workbook.add_worksheet("Audit Log")
            workbook.set_properties(
                {
                    "title": TITLE,
                    "author": self.env.user.name,
                }
            )
            sheet.set_footer('&"Times New Roman"&10Trang &P/&N')
            sheet.set_landscape()
            sheet.set_paper(9)
            sheet.fit_to_pages(1, 0)

            report_records = self._get_report_records(obj)
            date_from = obj.date_from
            date_to = obj.date_to

            formats = create_formats(workbook)
            rows = self._prepare_data(report_records)

            self._add_title(sheet, formats, report_records, date_from=date_from, date_to=date_to)
            self._add_header(sheet, formats)
            self._add_body(sheet, formats, rows)
