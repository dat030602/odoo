# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import base64
import io
from urllib.request import Request, urlopen

cols = [
    'stt',
    'code',
    'name',
    'uom',
    'quantity',
    '622',
    '627',
    'other_cost',
    'allocation_ratio',
    'price_total',
]
col_name = {
    'stt': 'STT',
    'code': 'Mã hàng',
    'name': 'Tên hàng',
    'uom': 'Đvt',
    'quantity': 'Số lượng',
    '622': 'Tổng CP Nhân Công TK 622',
    '627': 'Tổng CP SXC TK 627',
    'price_total': 'Thành tiền',
    'other_cost': 'Chi phí khác',
    'allocation_ratio': 'Tỷ lệ phân bổ',
}

class rp_average_period_xlsx(models.AbstractModel):
    _name = "report.biz_capital_price.rp_average_period_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "rp_average_period_xlsx"

    def generate_xlsx_report(self, workbook, data, docs):
        self = self.with_context(lang=self.env.user.lang)
        table_border_head = {
            "text_wrap": True,
            "align": "center",
            "border": True,
            "bold": True,
        }
        table_border_body = {
            "align": "left",
            "top": True,
            "bottom": True,
            "left": True,
            "right": True,
            'num_format': '#,##0.00',
        }

        def get_format(*arguments):
            normal_style = {
                "font_name": "Times New Roman",
                "font_size": 12,
                "valign": "vcenter",
                "align": "left",
                "text_wrap": True,
            }
            for arg in arguments:
                normal_style.update(arg)
            return workbook.add_format(normal_style)

        for o in docs:
            sheet = workbook.add_worksheet(f"Kiểm tra chi phí phân bổ 2% - {o.display_name}")
            sheet.set_landscape()
            sheet.set_paper(9)
            sheet.set_margins(0.5, 0.5, 0.3, 0.3)
            sheet.set_column(0, 0, 5)
            sheet.set_column(1, 1, 15)
            sheet.set_column(2, 2, 30)
            sheet.set_column(3, 3, 10)
            sheet.set_column(4, 99, 15)
            y_offset = 0
            sheet.set_row(y_offset, 25)
            sheet.merge_range(y_offset, 0, y_offset, 9, f"BẢNG CHI PHÍ PHÂN BỔ MUA HÀNG", get_format({'bold': True,'align': 'center'}))
            y_offset += 1
            sheet.merge_range(y_offset, 0, y_offset, 9, 
                f"Từ ngày: {o.from_date.strftime('%d/%m/%Y')} Đến ngày: {o.to_date.strftime('%d/%m/%Y')}", 
                get_format({'align': 'center','bold': True}))
            y_offset += 1

            # Header
            for col in cols:
                sheet.write(y_offset, cols.index(col), col_name[col], get_format(table_border_head))
            y_offset += 1

            # Body
            lines, sum_quantity = self.get_lines(o)
            sum_total_622 = sum_total_627 = sum_total = 0
            sum_total_other_cost = 0
            sum_allocation_ratio = 0
            for index,line in enumerate(lines):
                l622 = line['622']
                l627 = line['627']
                sum_total_622 += l622
                sum_total_627 += l627
                sum_total += l622 + l627 + line['other_cost']
                sum_total_other_cost += line['other_cost']
                allocation_ratio = round(line['quantity'] * 100/sum_quantity, 2) if sum_quantity else 0
                sheet.write(y_offset, cols.index('stt'), index + 1, get_format(table_border_body))
                sheet.write(y_offset, cols.index('code'), line['code'] or '', get_format(table_border_body))
                sheet.write(y_offset, cols.index('name'), line['name'] or '', get_format(table_border_body))
                sheet.write(y_offset, cols.index('uom'), line['uom'] or '', get_format(table_border_body))
                sheet.write(y_offset, cols.index('quantity'), line['quantity'], get_format(table_border_body))
                sheet.write(y_offset, cols.index('622'), l622, get_format(table_border_body))
                sheet.write(y_offset, cols.index('627'), l627, get_format(table_border_body))
                sheet.write(y_offset, cols.index('other_cost'), line['other_cost'], get_format(table_border_body))
                sheet.write(y_offset, cols.index('allocation_ratio'), f"{allocation_ratio} %", get_format(table_border_body))
                sheet.write(y_offset, cols.index('price_total'), l622 + l627 + line['other_cost'], get_format(table_border_body))
                y_offset += 1

            sheet.write(y_offset, cols.index('stt'), '', get_format(table_border_body, {'bold': True}))
            sheet.write(y_offset, cols.index('code'), '', get_format(table_border_body, {'bold': True}))
            sheet.write(y_offset, cols.index('name'), '', get_format(table_border_body, {'bold': True}))
            sheet.write(y_offset, cols.index('uom'), '', get_format(table_border_body, {'bold': True}))
            sheet.write(y_offset, cols.index('quantity'), sum_quantity, get_format(table_border_body, {'bold': True}))
            sheet.write(y_offset, cols.index('622'), sum_total_622, get_format(table_border_body, {'bold': True}))
            sheet.write(y_offset, cols.index('627'), sum_total_627, get_format(table_border_body, {'bold': True}))
            sheet.write(y_offset, cols.index('other_cost'), sum_total_other_cost, get_format(table_border_body, {'bold': True}))
            sheet.write(y_offset, cols.index('allocation_ratio'), "100 %", get_format(table_border_body, {'bold': True}))
            sheet.write(y_offset, cols.index('price_total'), sum_total, get_format(table_border_body, {'bold': True}))

    def sum_total_cost(self, o):
        sum_622 = sum_627 = 0
        value_622 = value_627 = 0
        for line in o.end_cost_allocation_ids:
            if line.cost_id.name.startswith('622'):
                sum_622 += line.total_cost
                value_622 += line.value
            if line.cost_id.name.startswith('627'):
                sum_627 += line.total_cost
                value_627 += line.value
        return sum_622, sum_627, value_622, value_627

    def get_lines(self, o):
        res = {}
        sum_quantity = 0
        for per in o.period_ids:
            for line in per.period_line_ids.filtered(lambda x: x.quantity_in_period != 0):
                sum_quantity += line.quantity_in_period
                prod = res.setdefault(line.product_id.id, {
                    'warehouse': per.warehouse_id.name,
                    'code': line.product_id.default_code or '',
                    'name': line.product_id.name or '',
                    'uom': line.product_id.uom_id.name or '',
                    'value': 0,
                    'quantity': 0,
                    '622': 0,
                    '627': 0,
                    'price_total': 0,
                    'other_cost': 0,
                })
                prod['quantity'] += line.quantity_in_period
                prod['value'] += line.unit_value
                for ad in line.allocation_details_by_account_ids:
                    if any([ac.code.startswith('622') for ac in ad.account_ids]):
                        prod['622'] += ad.allocated_value_for_product
                        continue
                    if any([ac.code.startswith('627') for ac in ad.account_ids]):
                        prod['627'] += ad.allocated_value_for_product
                        continue

                    prod['other_cost'] += ad.allocated_value_for_product

        return res.values(), sum_quantity
