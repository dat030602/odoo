# -*- coding: utf-8 -*-
from odoo import api, models, fields
from datetime import datetime, timedelta, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
FIELDS = [
    'product_code',"product_name","accounting_date",
    "document_number","explain","uom_id","qty_import","qty_export","qty_inv",'account_warehouse_code',
    'ctp_account_ids','partner_id','production_id','warehouse_id','factory_manager_name'
]

cols_name = {
    'product_code': 'Mã hàng',
    "product_name": 'Tên hàng',
    "accounting_date": 'Ngày hoạch toán',
    "document_number": 'Số chứng từ',
    "explain": 'Diễn giải',
    "uom_id": 'ĐVT',
    "qty_import": 'Nhập\nSố lượng',
    "qty_export": 'Xuất\nSố lượng',
    "qty_inv": 'Tồn\nSố lượng',
    'account_warehouse_code': 'TK kho',
    'ctp_account_ids': 'TK đối ứng',
    'partner_id': 'Tên đối tượng',
    'production_id': 'Lệnh sản xuất',
    'warehouse_id': 'Kho',
    'factory_manager_name': 'Người phụ trách sản xuất nhà máy'
}

class rp_material_detail_book_xlsx(models.AbstractModel):
    _name = 'report.biz_detailed_book_of_materials.rp_material_detail_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "rp_material_detail_book_xlsx"
    
    def generate_xlsx_report(self, workbook, data, o):
        self = self.with_context(lang=self.env.user.lang)
        self = self.sudo()
        o = o.sudo()
        image_content = {'font_name': 'Times New Roman', 'font_size': 22, 'bold': True, 'align': 'center', 'valign':'vcenter'}
        table_border_head = {
            'font_name': 'Times New Roman', 'font_size': 12, 'text_wrap': True, 
            'align': 'center','border':True,'bold':True,
        }
        table_border_body = {'font_name': 'Times New Roman', 'border': True, 'align': 'center'}

        def get_format(*arguments):
            normal_style = {'font_name': 'Times New Roman', 'font_size': 12,'valign':'vcenter'}
            for arg in arguments:
                normal_style.update(arg)
            return workbook.add_format(normal_style)

        sheet = workbook.add_worksheet("Số chi tiết vật liệu, dụng cụ")
        sheet.set_column(0,0,15)
        sheet.set_column(1,1,35)
        sheet.set_column(2,5,15)
        sheet.set_column(11,15,25)
        cols = self.get_cols(o)

        y_offset = 0

        sheet.merge_range(y_offset, 0, y_offset, len(cols) - 1, 'SỔ CHI TIẾT VẬT TƯ HÀNG HÓA', get_format({
            'bold': True,'align': 'center','font_size': 16
        }))
        y_offset +=1
        sheet.merge_range(y_offset, 0, y_offset, len(cols) - 1, 'Kho: %s; %s' % (', '.join(o.warehouse_ids.mapped('name')) if o.warehouse_ids else 'Tất cả',\
        'Từ %s đến %s'%(o.from_date.strftime('ngày %d tháng %m năm %Y'),o.to_date.strftime('ngày %d tháng %m năm %Y'))), get_format({
            'bold': True, 'align':'center'
        }))
       
        # Header
        y_offset+=1
        sheet.set_row(y_offset, 25)
        for index, col in enumerate(cols):
            name_field = cols_name[col]
            sheet.write(y_offset, index, name_field, get_format(table_border_head))
        y_offset +=1

        groups,products = self.get_lines(o)
        total_import = total_export = 0
        for warehouse, product_ids in groups.items():
            sum_inv = sum(len(ln['lines']) for ln in product_ids.values())
            for index, col in enumerate(cols):
                if col == 'product_code':
                    sheet.write(y_offset,index, '%s (%s)'  % (warehouse.name or '', sum_inv), get_format(table_border_body, {'bold': True,'align': 'left'}))
                    continue
                sheet.write(y_offset, index, '', get_format(table_border_body, {'bold': True,'align': 'left'}))
            y_offset +=1

            for product_id, vals in product_ids.items():
                lines = vals['lines']
                sum_import = vals['sum_import']
                sum_export = vals['sum_export']
                total_import += sum_import
                total_export += sum_export
                initial_line = self.get_initial_lines(o, cols, product_id, warehouse, vals)

                for index, col in enumerate(cols):
                    col_format = get_format(table_border_body, {'bold': True, 'align': 'left'})
                    if col in ['qty_import','qty_export','qty_inv']:
                        col_format = get_format(table_border_body, {'bold': True, 'align': 'center'})

                    sheet.write(y_offset, index, initial_line[col], col_format)

                y_offset +=1
                last_qty_inv = 0
                for line in sorted(lines, key=lambda x: x['accounting_date']):
                    for index, col in enumerate(cols):
                        col_format = get_format(table_border_body, {"align": 'left'})
                        if col in ['document_number','accounting_date','uom_id','qty_import','qty_export',
                            'qty_inv','account_warehouse_code','ctp_account_ids']:

                            col_format = get_format(table_border_body)
                        if col == 'accounting_date':
                            sheet.write(y_offset, index, line[col].strftime('%d/%m/%Y') if line[col] else '', col_format)
                        else:
                            sheet.write(y_offset, index, line[col], col_format)
                        if col == 'qty_inv':
                            last_qty_inv = line[col]
                    
                    y_offset +=1
                for index, col in enumerate(cols):
                    if col == 'explain':
                        sheet.write(y_offset,index, 'Tổng cộng mã hàng: %s'%(product_id.default_code or ''), get_format(table_border_body, {'bold': True,'align': 'left'}))
                        continue
                    if col == 'qty_import':
                        sheet.write(y_offset,index, sum_import, get_format(table_border_body, {'bold': True,'align': 'center'}))
                        continue
                    if col == 'qty_export':
                        sheet.write(y_offset,index, sum_export, get_format(table_border_body, {'bold': True,'align': 'center'}))
                        continue
                    if col == 'qty_inv':
                        sheet.write(y_offset,index, last_qty_inv, get_format(table_border_body, {'bold': True,'align': 'center'}))
                        continue
                    sheet.write(y_offset, index, '', get_format(table_border_body, {'bold': True,'align': 'left'}))
                y_offset +=1
        
        total_val = {
            'product_code': 'Tổng số dòng: %s' % (y_offset - 3),
            "product_name": '',
            "accounting_date": '',
            "document_number": '',
            "explain": '',
            "uom_id": '',
            "qty_import": round(total_import, 3),
            "qty_export": round(total_export, 3),
            "qty_inv": '',
            'account_warehouse_code': '',
            'ctp_account_ids': '',
            'partner_id': '',
            'production_id': '',
            'warehouse_id': '',
            'factory_manager_name': ''
        }
        for index, col in enumerate(cols):
            col_format = get_format(table_border_head, {"align": 'left'})
            if col in ['document_number','accounting_date','uom_id','qty_import','qty_export',
                'qty_inv','account_warehouse_code','ctp_account_ids']:

                col_format = get_format(table_border_head)

            sheet.write(y_offset, index, total_val[col], col_format)
        
        y_offset+=1

    def get_lines(self, o):
        groups = {}
        product_ids = []
        for line in o.line_ids.filtered(lambda x: not x.is_total):
            line = line.sudo()
            warehouse_id = line.warehouse_id
            if line.product_id.id not in product_ids:
                product_ids.append(line.product_id.id)

            if warehouse_id not in groups:
                groups[warehouse_id] = {}

            prod = groups[warehouse_id].setdefault(line.product_id, {
                'sum_import': 0,
                'sum_export': 0,
                'lines': []
            })
            prod['sum_import'] += line.qty_import
            prod['sum_export'] += line.qty_export
            prod['lines'].append({
                'product_code': line.product_code or '',
                "product_name": line.product_id.name or '',
                "accounting_date": line.accounting_date,
                "document_number": line.document_number or '',
                "explain": line.explain or '',
                "uom_id": line.uom_id.name or '',
                "qty_import": round(line.qty_import, 3),
                "qty_export": round(line.qty_export, 3),
                "qty_inv": line.qty_inv,
                'account_warehouse_code': line.account_warehouse_code or '',
                'ctp_account_ids': line.ctp_account_ids and ','.join(line.ctp_account_ids.mapped('code')) or '',
                'partner_id': line.object_name or '',
                'production_id': line.production_id.name or '',
                'warehouse_id': line.warehouse_id.name or '',
                'factory_manager_name': line.factory_manager_name
            })

        return groups,product_ids


    def get_cols(self, o):
        if not o.export_fields_ids:
            return FIELDS

        return o.export_fields_ids.filtered(lambda x: x.is_selected).mapped("field_id").mapped("name")


    def format_float_number(self, num):
        if not num:
            return 0

        number = float(num)
        if number % 1 == 0:
            return "{:,.0f}".format(number).replace(',','.')
        else:
            number_format = "{:,.2f}".format(number).rstrip('0')
            numbers = number_format.split('.')
            return numbers[0].replace(',','.') + ',' + numbers[1]

    def get_initial_lines(self, o, cols, product_id, warehouse, vals):
        initial_balance = o.get_initial_balance(product_id,warehouse)
        lines = vals['lines']
        # sum_import = vals['sum_import']
        # sum_export = vals['sum_export']
        return {
            'product_code': '         %s (%s)'  % (product_id.name or '', len(lines)),
            "product_name": '',
            "accounting_date": '',
            "document_number": '',
            "explain": 'Số dư đầu kỳ',
            "uom_id": '',
            "qty_import": '',
            "qty_export": '',
            "qty_inv": initial_balance,
            'account_warehouse_code': '',
            'ctp_account_ids': '',
            'partner_id': '',
            'production_id': '',
            'warehouse_id': '',
            'factory_manager_name': ''
        }

