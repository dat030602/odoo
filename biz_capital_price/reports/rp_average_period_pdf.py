import json

from odoo import api, fields, models, _
from datetime import datetime, timedelta


class rp_average_period_pdf(models.AbstractModel):
    _name = 'report.biz_capital_price.rp_average_period_pdf'
    _description = 'rp_average_period_pdf'

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

        return {
            'sum_622': sum_622,
            'sum_627': sum_627,
            'value_622': value_622,
            'value_627': value_627
        }

    def get_lines(self, o):
        res = {}
        sum_quantity = 0
        for per in o.period_ids:
            for line in per.period_line_ids.filtered(lambda x: x.quantity_in_period != 0):
                prod = res.setdefault(line.product_id.id, {
                    'warehouse': per.warehouse_id.name or '',
                    'code': line.product_id.default_code or '',
                    'name': line.product_id.name or '',
                    'uom': line.product_id.uom_id.name or '',
                    'quantity': 0,
                    'value': 0,
                    '622': 0,
                    '627': 0,
                    'price_total': 0,
                    'other_cost': 0,
                })
                sum_quantity += line.quantity_in_period
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

        sum_622 = sum_627 = sum_total = 0
        sum_other_cost = 0
        sum_allocation_ratio = 0
        
        for line in res.values():
            line['price_total'] = line['622'] + line['627'] + line['other_cost']
            line['allocation_ratio'] = sum_quantity and round(line['quantity'] * 100 / sum_quantity, 2) or 0
            sum_allocation_ratio += line['allocation_ratio']

            sum_622 += line['622']
            sum_627 += line['627']
            sum_total += line['price_total']
            sum_other_cost += line['other_cost']
        return {
            'lines': res.values(),
            'sum_622': sum_622,
            'sum_627': sum_627,
            'sum_quantity': sum_quantity,
            'sum_total': sum_total,
            'sum_other_cost': sum_other_cost,
            'sum_allocation_ratio': sum_allocation_ratio,
        }


    def format_float_number(self, number):
        number_format = 0
        if number % 1 == 0:
            number_format = "{:,.0f}".format(number)
        else:
            number_format = "{:,.2f}".format(number)
        return number_format

    def get_date(self, date):
        if not date:
            return ''
        return date.strftime('%d/%m/%Y')

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['average.price.end.period.mass'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'average.price.end.period.mass',
            'docs': docs,
            'get_lines': self.get_lines,
            'sum_total_cost': self.sum_total_cost,
            'format_float_number': self.format_float_number,
            'get_date': self.get_date,
        }