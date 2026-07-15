# -*- coding: utf-8 -*-
from odoo import models
from collections import defaultdict
from datetime import timedelta, time, datetime
col_name = {
    'stt': 'STT',
    'nvl_code': 'Mã NVL',
    'nvl_name': 'Tên NVL',
    'product_code': 'Mã thành phẩm',
    'product_name': 'Tên thành phẩm',
    'uom': 'Đơn vị tính',
    'sl_nvl': 'Số lượng NVL',
    'value_nvl': 'Giá trị NVL',
    'direct_material_6211': 'NVL trực tiếp (TK 6211)',
    'indirect_material_6272': 'NVL gián tiếp (TK 6272)',
    'direct_labor_622': 'Nhân công trực tiếp (TK 622)',
    'indirect_labor_6271': 'Nhân công gián tiếp (TK 6271)',
    'depreciation_6274': 'Khấu hao (TK 6274)',
    'outsourcing_cost_627': 'Chi phí mua ngoài (Những TK 627 còn lại)',
    'other_cost_6278': 'Chi phí khác (TK 6278)',
    'total': 'Tổng',
    'material_quantity': 'Số lượng thành phẩm',
    'uom_cost': 'Giá thành đơn vị',
    'tylethuhoi': 'TP thu hồi (%)',
}
cols = {c: i for i, c in enumerate(col_name)}

class CostingReportXlsx(models.AbstractModel):
    _name = "report.biz_capital_price.costing_rp_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "costing_rp_xlsx"

    def generate_xlsx_report(self, workbook, data, docs):
        self = self.with_context(lang=self.env.user.lang)
        table_border_head = {
            "text_wrap": True,
            "align": "center",
            "border": True,
            'border_color': '#7DA2CE',
            "bold": True,
            'bg_color': '#ADC7E7',
            'font_color': 'red',
        }
        table_title = {
            "text_wrap": True,
            "align": "center",
            "bold": True,
        }
        table_border_body = {
            "align": "left",
            'num_format': '#,##0.00',
        }
        table_number = {
            "align": "right",
            'num_format': '#,##0.00',
        }
        table_border_sum_number = {
            "align": "right",
            "top": True,
            "bottom": True,
            "left": True,
            "right": True,
            'num_format': '#,##0.00',
            'bg_color': '#D7D7D7',
            "border": True,
            'border_color': '#7DA2CE',
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

        for o in docs.filtered(lambda o: o.is_finished_products):
            sheet = workbook.add_worksheet(f"Báo cáo giá thành - {o.display_name}")
            sheet.set_landscape()
            sheet.set_paper(9)
            sheet.set_margins(0.5, 0.5, 0.3, 0.3)
            sheet.set_column(0, 0, 8)
            sheet.set_row(0, 20)  
            sheet.set_column(1, 1, 15)
            sheet.set_row(1, 15)  
            sheet.set_column(2, 2, 25)
            sheet.set_column(3, 3, 30)
            sheet.set_column(4, 99, 15)
            y_offset = 0
            sheet.merge_range(y_offset, 0, y_offset, 14, 'BẢNG TÍNH GIÁ THÀNH', get_format(table_title))
            y_offset += 1
            sheet.merge_range(y_offset, 0, y_offset, 14, 'Kỳ tính giá thành: Kỳ tính giá thành TP từ ngày %s đến ngày %s' %(o.from_date, o.to_date), get_format(table_title))
            y_offset += 1
        
            # Header
            start_group, end_group = 8, 15

            for col in cols:
                col_idx = cols[col]
                if start_group <= col_idx <= end_group:
                    sheet.write(y_offset+1, col_idx, col_name[col], get_format(table_border_head))
                else:
                    sheet.merge_range(
                        y_offset, col_idx,
                        y_offset+1, col_idx,
                        col_name[col],
                        get_format(table_border_head)
                    )

            sheet.merge_range(
                y_offset, start_group, y_offset, end_group,
                "Giá thành", get_format(table_border_head)
            )
            y_offset += 2

            # # Body
            lines, sums = self.get_lines(o)
            for index, line in enumerate(lines):
                nvl_ids, sl_tp, value_tp = self.get_nvl_ids(o,line['product_id'])
                line.update({
                    'sl_nvl': sl_tp, 
                    'value_nvl': value_tp,
                    'tylethuhoi': line.get('material_quantity',0) * 100 / sl_tp if sl_tp else 0,
                })
                for ind,col in enumerate(col_name.keys()):
                    if col in ['stt','uom']:
                        sheet.write(y_offset, ind, index + 1 if col == 'stt' else line.get(col,''), get_format(table_border_body, {'align': 'center'}))
                    elif col in ['warehouse','nvl_code','nvl_name','product_name','product_code']:
                        sheet.write(y_offset, ind, line.get(col,''), get_format(table_border_body))

                    elif col in ['sl_nvl','value_nvl','direct_material_6211','indirect_material_6272',
                        'direct_labor_622','indirect_labor_6271','depreciation_6274',
                        'outsourcing_cost_627','other_cost_6278','total']:
                        sheet.write_number(y_offset, ind, line.get(col,0), get_format(table_number))
                    elif col in ['material_quantity','uom_cost']:
                        sheet.write_number(y_offset, ind, line.get(col,0), get_format(table_border_body, {'align': 'center'}))
                    elif col == 'tylethuhoi':
                        sheet.write(y_offset, ind, f"{line.get(col,0):.2f}%", get_format(table_border_body, {'align': 'center'}))

                y_offset += 1
                # Get NVL
                for nvl_id in nvl_ids.values():
                    nvl_id.update({
                        'product_name': line['product_name'],
                        'product_code': line['product_code'],
                    })
                    for nvl_ind, col in enumerate(col_name.keys()):
                        if col in ['stt','uom']:
                            sheet.write(y_offset, nvl_ind, nvl_id.get(col,'') or '', get_format(table_border_body, {'align': 'center'}))
                        elif col in ['warehouse','nvl_code','nvl_name','product_name','product_code', 'tylethuhoi']:
                            sheet.write(y_offset, nvl_ind, nvl_id.get(col,'') or '', get_format(table_border_body))

                        elif col in ['sl_nvl','value_nvl','direct_material_6211','indirect_material_6272',
                            'direct_labor_622','indirect_labor_6271','depreciation_6274',
                            'outsourcing_cost_627','other_cost_6278','total']:
                            sheet.write_number(y_offset, nvl_ind, nvl_id.get(col,0), get_format(table_number))
                        elif col in ['material_quantity','uom_cost']:
                            sheet.write_number(y_offset, nvl_ind, nvl_id.get(col,0), get_format(table_border_body, {'align': 'center'}))

                    y_offset += 1

            for index, key in enumerate(col_name.keys()):
                if key in ['stt','warehouse','product_code','sl_nvl','value_nvl','product_name','uom','nvl_code','nvl_name']:
                    sheet.write(y_offset, index, '', get_format())
                elif key in ['material_quantity','uom_cost','tylethuhoi']:
                    sheet.write_number(y_offset, index, sums.get(key,0), get_format(table_border_sum_number, {'align': 'center'}))
                else:
                    sheet.write_number(y_offset, index, sums.get(key,0), get_format(table_border_sum_number))

            y_offset += 7
            
            sheet.write(y_offset, 3, 'Người lập', get_format(table_title))
            sheet.merge_range(y_offset, 6, y_offset, 7, 'Kế toán trưởng', get_format(table_title))
            sheet.merge_range(y_offset, 10, y_offset, 11, 'Thứ trưởng đơn vị', get_format(table_title))
            y_offset += 1
            
            chief_accountant_id = o.env['ir.config_parameter'].sudo().get_param('ccv_sql.chief_accountant_id', False)
            chief_accountant = o.env['res.users'].sudo().search([('id', '=', int(chief_accountant_id))]) if chief_accountant_id else False
            unit_head_id = o.env['ir.config_parameter'].sudo().get_param('ccv_sql.unit_head_id', False)
            unit_head = o.env['res.users'].sudo().search([('id', '=', int(unit_head_id))]) if unit_head_id else False
            
            sheet.write(y_offset, 3, self.env.user.name_without_position or self.env.user.name, get_format(table_border_body, {'align': 'center'}))
            sheet.merge_range(y_offset, 6, y_offset, 7, chief_accountant and (chief_accountant.name_without_position or chief_accountant.name) or '', get_format(table_border_body, {'align': 'center'}))
            sheet.merge_range(y_offset, 10, y_offset, 11, unit_head and (unit_head.name_without_position or unit_head.name) or '', get_format(table_border_body, {'align': 'center'}))

    def get_lines(self, o):
        result = {}
        sums = defaultdict(float)
        for per in o.period_ids:
            for line in per.period_line_ids.filtered(lambda x: x.quantity_in_period != 0):
                res = result.setdefault(line.product_id.id, {
                    'product_id': line.product_id.id,
                    'warehouse': per.warehouse_id.name or '',
                    'product_code': line.product_id.default_code or '',
                    'product_name': line.product_id.name or '',
                    'uom': line.product_id.uom_id.name or '',
                    'direct_material_6211': 0,
                    'indirect_material_6272': 0,
                    'direct_labor_622': 0,
                    'indirect_labor_6271': 0,
                    'depreciation_6274': 0,
                    'outsourcing_cost_627': 0,
                    'other_cost_6278': 0,
                    'total': 0,
                    'material_quantity': 0,
                    'uom_cost': [],
                })

                specific_codes = {'6272', '6271', '6274', '6278', '6221'}
                totals = {code: 0 for code in specific_codes}
                totals['627'] = 0  
                totals['total'] = line.value_621

                for allocation_line in line.allocation_details_by_account_ids:
                    for account in allocation_line.account_ids:
                        code = account.code
                        if code in specific_codes:
                            totals[code] += allocation_line.allocated_value_for_product
                            totals['total'] += allocation_line.allocated_value_for_product
                        elif code.startswith('627'):
                            totals['627'] += allocation_line.allocated_value_for_product
                            totals['total'] += allocation_line.allocated_value_for_product
                            
                sums['indirect_material_6272'] += totals['6272']
                sums['direct_labor_622'] += totals['6221']
                sums['indirect_labor_6271'] += totals['6271']
                sums['depreciation_6274'] += totals['6274']
                sums['outsourcing_cost_627'] += totals['627']
                sums['other_cost_6278'] += totals['6278']
                sums['total'] += totals['total']
                sums['direct_material_6211'] += line.value_621
                sums['material_quantity'] += line.quantity_in_period

                res['direct_material_6211'] += line.value_621
                res['indirect_material_6272'] += totals['6272']
                res['direct_labor_622'] += totals['6221']
                res['indirect_labor_6271'] += totals['6271']
                res['depreciation_6274'] += totals['6274']
                res['outsourcing_cost_627'] += totals['627']
                res['other_cost_6278'] += totals['6278']
                res['total'] += totals['total']
                res['material_quantity'] += line.quantity_in_period
                res['uom_cost'].append(line.value_per_unit)  

        for line in result.values():
            line['uom_cost'] = sum(line['uom_cost']) / len(line['uom_cost']) if line['uom_cost'] else 0

        return list(result.values()), sums

    def get_nvl_ids(self, o, product_id):
        lines = {}
        from_date = datetime.combine(o.from_date, time.min) - timedelta(hours=7)
        to_date = datetime.combine(o.to_date, time.max) - timedelta(hours=7)
        move_ids = self.env['stock.move'].search([
            ('product_id', '=', product_id),
            ('production_id.date_planned_start', '>=', from_date),
            ('production_id.date_planned_start', '<=', to_date),
            ('production_id', '!=', False),
        ])
        sl_tp = 0
        value_tp = 0 

        production_ids = move_ids.mapped('production_id')
        layers = (production_ids.move_raw_ids + production_ids.move_finished_ids + production_ids.scrap_ids.move_id).stock_valuation_layer_ids
        for layer in layers:
            if layer.stock_move_id.location_id.usage == 'production':
                if not value_tp:
                    value_tp = abs(layer.unit_cost)
                continue

            if layer.stock_move_id.location_dest_id.usage != 'production':
                continue

            if layer.uom_id.is_ton:
                sl_tp += abs(layer.quantity)

            tmp = lines.setdefault(layer.product_id, {
                'nvl_code': layer.product_id.default_code or '',
                'nvl_name': layer.product_id.name or '',
                'sl_nvl': 0,
                'value_nvl': layer.unit_cost,
                'direct_material_6211': 0,
                'uom': layer.uom_id.name or '',
            })
            tmp['sl_nvl'] += abs(layer.quantity)
            tmp['direct_material_6211'] += abs(layer.value)
        return lines, sl_tp, value_tp