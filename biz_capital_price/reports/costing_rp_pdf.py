import json

from odoo import api, fields, models, _
from datetime import datetime, timedelta, time
from collections import defaultdict

class CostingReporPdf(models.AbstractModel):
    _name = 'report.biz_capital_price.costing_rp_pdf'
    _description = 'costing_rp_pdf'

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
        return lines.values(), sl_tp, value_tp
    
    def format_float_number(self, number):
        number_format = 0
        if number % 1 == 0:
            number_format = "{:,.0f}".format(number)
        else:
            number_format = "{:,.2f}".format(number)
        return number_format
    
    def get_chief_accountant(self):
        chief_accountant_id = self.env['ir.config_parameter'].sudo().get_param('ccv_sql.chief_accountant_id', False)
        chief_accountant = self.env['res.users'].sudo().search([('id', '=', int(chief_accountant_id))]) if chief_accountant_id else False
        return chief_accountant and chief_accountant.name_without_position or ''
    
    def get_unit_head(self):
        unit_head_id = self.env['ir.config_parameter'].sudo().get_param('ccv_sql.unit_head_id', False)
        unit_head = self.env['res.users'].sudo().search([('id', '=', int(unit_head_id))]) if unit_head_id else False
        return unit_head and unit_head.name_without_position or ''
    
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['average.price.end.period.mass'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'average.price.end.period.mass',
            'docs': docs,
            'get_lines': self.get_lines,
            'format_float_number': self.format_float_number,
            'get_chief_accountant': self.get_chief_accountant,
            'get_unit_head': self.get_unit_head,
            'get_nvl_ids': self.get_nvl_ids,
        }