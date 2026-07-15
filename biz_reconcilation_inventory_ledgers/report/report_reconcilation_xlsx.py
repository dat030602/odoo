# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime, timedelta

class ReportReconcilationXlsx(models.AbstractModel):
    _name = 'report.biz_reconcilation_inventory_legers.rp_reconcilation_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Report Reconcilation Xlsx'
    
    def generate_xlsx_report(self, workbook, data, o):
        self = self.with_context(lang=self.env.user.lang)
        table_border_head = {'font_name': 'Times New Roman', 'font_size': 10, 'text_wrap': True, 'align': 'center','border':True,'bold':True, 'bg_color': '#B8CCE4'}
        table_border_body = {'font_name': 'Times New Roman', 'font_size': 10, 'align': 'left','border':True,'num_format': '#,###'}
        table_border_body_right = {'font_name': 'Times New Roman', 'font_size': 10, 'align': 'right','border':True,'num_format': '#,###'}
        table_border_body_total = {'font_name': 'Times New Roman', 'font_size': 10, 'align': 'right','border':True,'num_format': '#,###', 'bg_color': '#CFCFCF'}
        not_border_body = {'font_name': 'Times New Roman', 'font_size': 10, 'align': 'center','valign':'vcenter','num_format': '#,###'}
        table_border_body_right_red = {'font_name': 'Times New Roman', 'font_size': 10, 'align': 'right','border':True,'color': 'red', 'num_format': '0;[Red] (-#,###);0'}
        
        def get_format(*arguments):
            normal_style = {'font_name': 'Times New Roman', 'font_size': 12,'valign':'vcenter','align': 'left'}
            for arg in arguments:
                normal_style.update(arg)
            return workbook.add_format(normal_style)

        sheet = workbook.add_worksheet("BÁO CÁO ĐỐI CHIẾU KHO VÀ SỔ CÁI")
        sheet.set_column(0,10,20)

        y_offset = 0
        sheet.merge_range(y_offset, 0, y_offset, 10, 'BÁO CÁO ĐỐI CHIẾU KHO VÀ SỔ CÁI', 
            get_format({'align': 'center','font_size': 14, 'bold': True,'bottom': 1, 'top': 1}))
        y_offset +=1
        
        month = o.from_date.strftime('%m') if o.from_date else '......'
        year = o.from_date.year if o.from_date else '.....'
        period_text = f"Kỳ đối chiếu: Ngày; Tháng {month} năm {year}"
        
        sheet.merge_range(y_offset, 0, y_offset, 10, period_text, 
            get_format({'align': 'center','font_size': 13, 'bold': True,'bottom': 1, 'top': 1}))
        y_offset +=1
        
        sheet.merge_range(y_offset, 0,y_offset+1, 0, 'Kỳ đối chiếu', get_format(table_border_head))
        sheet.merge_range(y_offset, 1,y_offset,   3, 'Theo sổ cái', get_format(table_border_head))
        sheet.merge_range(y_offset, 4,y_offset,   6, 'Theo sổ kho', get_format(table_border_head))
        sheet.merge_range(y_offset, 7,y_offset,   9, 'Chênh lệch', get_format(table_border_head))
        sheet.merge_range(y_offset, 10,y_offset+1,10,  'Chi tiết chênh lệch ', get_format(table_border_head))
        sheet.write(y_offset +1, 1, 'Phát sinh Nợ', get_format(table_border_head))
        sheet.write(y_offset +1, 2, 'Phát sinh Có', get_format(table_border_head))
        sheet.write(y_offset +1, 3, 'Số dư', get_format(table_border_head))
        sheet.write(y_offset +1, 4, 'Nhập kho', get_format(table_border_head))
        sheet.write(y_offset +1, 5, 'Xuất kho', get_format(table_border_head))
        sheet.write(y_offset +1, 6, 'Tồn kho', get_format(table_border_head))
        sheet.write(y_offset +1, 7, 'PS Nợ - Nhập kho', get_format(table_border_head))
        sheet.write(y_offset +1, 8, 'PS Có - Xuất kho', get_format(table_border_head))
        sheet.write(y_offset +1, 9, 'Số dư - Tồn kho', get_format(table_border_head))
        y_offset +=2
        # số dư dòng đầu tiên dòng 1
        previous_day = o.from_date - timedelta(days=1)
        domain = [('account_id.is_compare', '=', True),
                  ('parent_state', '=', 'posted')
                  ]
        if o.from_date:
            domain.append(('date', '<', o.from_date))
        move_lines = self.env['account.move.line'].search(domain)
        debit_credit_sum = 0
        if move_lines:
            debit_credit_sum = sum(move_lines.mapped(lambda line: line.debit - line.credit))
            
        # tồn kho dòng đầu tiên dòng 6
        history_day = o.from_date - timedelta(seconds=1)
        history_record = self.env['stock.quantity.history'].create({
            'inventory_datetime': history_day,
        })
        context = dict(self.env.context, active_model='stock.valuation.layer')
        action = history_record.with_context(context).open_at_date()
        total_value = 0
        if 'domain' in action:
            records = self.env['stock.valuation.layer'].search(action['domain'])
            valid_records = records.filtered(lambda r: r.quantity != 0)
            total_value = sum(valid_records.mapped('value'))
        value_difference = debit_credit_sum - total_value

        
        sheet.write(y_offset, 0, previous_day.strftime('%d/%m/%Y'),  get_format(table_border_body,{'bold': True}))
        sheet.write(y_offset, 1, '0',  get_format(table_border_body_right,{'bold': True}))
        sheet.write(y_offset, 2, '0',  get_format(table_border_body_right,{'bold': True}))
        sheet.write(y_offset, 3, debit_credit_sum or '0',  get_format(table_border_body_right,{'bold': True}))
        sheet.write(y_offset, 4, '0',  get_format(table_border_body_right,{'bold': True}))
        sheet.write(y_offset, 5, '0',  get_format(table_border_body_right,{'bold': True}))
        if total_value >= 0:
            sheet.write(y_offset, 6, total_value,  get_format(table_border_body_right,{'bold': True}))
        else:
            sheet.write(y_offset, 6, total_value,  get_format(table_border_body_right_red),{'bold': True})
        sheet.write(y_offset, 7, '0',  get_format(table_border_body_right,{'bold': True}))
        sheet.write(y_offset, 8, '0',  get_format(table_border_body_right,{'bold': True}))
        sheet.write(y_offset, 9, value_difference,  get_format(table_border_body_right,{'bold': True}))
        sheet.write(y_offset, 10, '',  get_format(table_border_body_right,{'bold': True}))
        y_offset +=1
        
        # các dòng chi tiết
        total_debit_sum = 0
        total_credit_sum = 0
        total_import_sum = 0
        total_export_sum = 0
        ps_debit_inventory_sum = 0
        ps_credit_inventory_sum = 0
        
        balance = debit_credit_sum
        total_stock = total_value
        current_date = o.from_date
        line_count = 0
        
        while current_date <= o.to_date:
            # Phát sinh nợ
            debit_domain = [
                ('account_id.is_compare', '=', True),
                ('date', '=', current_date),
                ('parent_state', '=', 'posted')
            ]
            total_debit = sum(self.env['account.move.line'].search(debit_domain).mapped('debit'))
            # Phát sinh có
            credit_domain = [
                ('account_id.is_compare', '=', True),
                ('date', '=', current_date),
                ('parent_state', '=', 'posted')
            ]
            total_credit = sum(self.env['account.move.line'].search(credit_domain).mapped('credit'))
            # CỘt số dư
            balance = balance + total_debit - total_credit
            # Cột nhập kho
            import_stock_domain = [
                ('create_date', '=', current_date),
                ('quantity', '>', 0),
                ('stock_move_id.location_id.usage', 'in', ['supplier', 'production', 'inventory'])
            ]
            total_import = sum(self.env['stock.valuation.layer'].search(import_stock_domain).mapped('value'))
            # Cột xuất kho
            export_move_domain = [
                ('create_date', '=', current_date),
                ('quantity', '<', 0),
                ('stock_move_id.location_id.usage', '=', 'customer')
            ]
            total_export = sum(self.env['stock.valuation.layer'].search(export_move_domain).mapped('value'))
            # Tồn kho
            total_stock = total_stock + total_import - total_export
            # PS Nợ - Nhập kho
            ps_debit_inventory = total_debit - (abs(total_import))
            # PS Có - Xuất kho
            ps_credit_inventory = total_credit - (abs(total_export))
            # Số dư - Tồn kho
            balance_inventory = balance - total_stock
            # Sum
            total_debit_sum += total_debit
            total_credit_sum += total_credit
            total_import_sum += abs(total_import)
            total_export_sum += abs(total_export)
            ps_debit_inventory_sum += ps_debit_inventory
            ps_credit_inventory_sum += ps_credit_inventory
            # balance_inventory_sum += balance_inventory
            
            sheet.write(y_offset, 0, current_date.strftime('%d/%m/%Y'),  get_format(table_border_body))
            sheet.write(y_offset, 1, total_debit,  get_format(table_border_body_right))
            sheet.write(y_offset, 2, total_credit,  get_format(table_border_body_right))
            sheet.write(y_offset, 3, balance,  get_format(table_border_body_right))
            sheet.write(y_offset, 4, abs(total_import),  get_format(table_border_body_right))
            sheet.write(y_offset, 5, abs(total_export),  get_format(table_border_body_right))
            sheet.write(y_offset, 6, total_stock,  get_format(table_border_body_right))
            if ps_debit_inventory >= 0:
                sheet.write(y_offset, 7, ps_debit_inventory,  get_format(table_border_body_right))
            else:
                sheet.write(y_offset, 7, ps_debit_inventory,  get_format(table_border_body_right_red)) 
            
            if ps_credit_inventory >= 0:
                sheet.write(y_offset, 8, ps_credit_inventory,  get_format(table_border_body_right))
            else:
                sheet.write(y_offset, 8, ps_credit_inventory,  get_format(table_border_body_right_red))
            if balance_inventory >= 0:  
                sheet.write(y_offset, 9, balance_inventory,  get_format(table_border_body_right))
            else:
                sheet.write(y_offset, 9, balance_inventory,  get_format(table_border_body_right_red))
            sheet.write(y_offset, 10, 'Xem chi tiết',  get_format(table_border_body_right,{'align': 'center'}))
            line_count += 1
            current_date += timedelta(days=1)
            y_offset += 1
            
        # dòng tổng   
        sheet.write(y_offset, 0, 'Số dòng = ' + str(line_count),  get_format(table_border_body_total,{'align': 'left'}))
        sheet.write(y_offset, 1, total_debit_sum or '0',  get_format(table_border_body_total))
        sheet.write(y_offset, 2, total_credit_sum or '0',  get_format(table_border_body_total))
        sheet.write(y_offset, 3, '',  get_format(table_border_body_total))
        sheet.write(y_offset, 4, total_import_sum or '0',  get_format(table_border_body_total))
        sheet.write(y_offset, 5, total_export_sum or '0',  get_format(table_border_body_total))
        sheet.write(y_offset, 6, '',  get_format(table_border_body_total))
        sheet.write(y_offset, 7, ps_debit_inventory_sum or '0',  get_format(table_border_body_total))
        sheet.write(y_offset, 8, ps_credit_inventory_sum or '0',  get_format(table_border_body_total))
        sheet.write(y_offset, 9, '',  get_format(table_border_body_total))
        sheet.write(y_offset, 10, '',  get_format(table_border_body_total,{'align': 'center'}))