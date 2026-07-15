from odoo import models, fields, api
import logging
import math
import decimal
import json
import csv
import re
import os
import sys
import collections
import itertools
import operator
import functools
import random
import statistics
from datetime import datetime, date, time, timedelta
from calendar import monthrange

_logger = logging.getLogger(__name__)

class SalaryCommissionCalculation(models.Model):
    """Tính toán hoa hồng theo công thức"""
    _name = 'salary.commission.calculation'
    _description = 'Salary Commission Calculation'
    _order = 'commission_type'

    name = fields.Char(string='Tên', required=True)
    commission_type = fields.Selection([
        ('monthly', 'Hoa hồng tháng'),
        ('monthly_sr', 'Hoa hồng tháng SR'),
        ('humic_fertilizer', 'Hoa hồng Humic & Phân bón lá'),
        ('new_dealer', 'Hoa hồng theo SL mở đại lý mới'),
        ('team_building', 'Hoa hồng thưởng xây dựng đội nhóm'),
        ('commercial_discount', 'Hoa hồng chiết khấu thương mại'),
    ], string='Loại hoa hồng', required=True)
    
    # Field tính toán
    calculation_field = fields.Char(
        string='Field tính toán',
        help='Tên field sẽ được sử dụng trong công thức tính toán',
        required=True
    )
    
    # Công thức tính toán
    formula = fields.Text(
        string='Công thức', 
        required=True,
        help='Công thức tính toán. Sử dụng biến "records" cho dữ liệu đầu vào và "result" cho kết quả cuối cùng.\n'
             'Các thư viện có sẵn: math, decimal, statistics, random, datetime, re, json, collections, itertools, operator, functools\n'
             'Ví dụ:\n'
             '- result = sum([r.amount for r in records]) * 0.05\n'
             '- result = math.ceil(records * 0.1) if records > 1000000 else records * 0.05\n'
             '- result = statistics.mean([r.amount for r in records]) * 0.03\n'
             '- result = max(0, records - 500000) * 0.02'
    )
    
    # Nhân viên áp dụng
    employee_ids = fields.Many2many(
        'hr.employee', 
        'salary_commission_calculation_employee_rel',
        'calculation_id', 
        'employee_id',
        string='Nhân viên áp dụng'
    )
    # Trạng thái
    active = fields.Boolean(string='Kích hoạt', default=True)
    
    # Thông tin bổ sung
    description = fields.Text(string='Mô tả')
    
    currency_id = fields.Many2one(
        'res.currency', 
        string='Loại tiền tệ', 
        default=lambda self: self.env.company.currency_id
    )

    @api.onchange('commission_type')
    def _onchange_commission_type(self):
        """Set default values based on commission_type"""
        if self.commission_type:
            # Set default calculation_field based on commission_type
            if self.commission_type == 'monthly':
                self.calculation_field = 'personnel_commission_ids'
            elif self.commission_type == 'monthly_sr':
                self.calculation_field = 'sales_commission_employee_ids'
            elif self.commission_type == 'humic_fertilizer':
                self.calculation_field = 'humic_sales_detail_ids'
            elif self.commission_type == 'new_dealer':
                self.calculation_field = 'customer_open_list_ids'
            elif self.commission_type == 'team_building':
                self.calculation_field = 'bonus_commission_ids'

    def name_get(self):
        res = []
        # Mapping commission_type values to display names
        commission_type_mapping = {
            'monthly': 'Hoa hồng tháng',
            'monthly_sr': 'Hoa hồng tháng SR',
            'humic_fertilizer': 'Hoa hồng Humic & Phân bón lá',
            'new_dealer': 'Hoa hồng theo SL mở đại lý mới',
            'team_building': 'Hoa hồng thưởng xây dựng đội nhóm',
            'commercial_discount': 'Hoa hồng chiết khấu thương mại',
        }
        
        for record in self:
            if record.commission_type:
                commission_type_display = commission_type_mapping.get(record.commission_type, record.commission_type)
            else:
                commission_type_display = 'Chưa chọn'
            res.append((record.id, f"CT: {commission_type_display} - {record.name or ''}"))
        return res

    def calculate_commission(self, summary_id):
        """
        Tính toán hoa hồng từ summary_id, tự lấy field và tính toán theo công thức
        
        Args:
            summary_id: ID của salary.sales.summary
            
        Returns:
            float: Số tiền hoa hồng sau khi tính toán
        """
        self.ensure_one()
        
        if not self.formula or not summary_id:
            return 0.0
        
        try:
            # Lấy summary
            summary = self.env['salary.sales.summary'].browse(summary_id)
            if not summary.exists():
                return 0.0

            if self.commission_type == 'team_building' and not self._is_team_building_applicable_period(summary):
                return 0.0
            
            # Lấy dữ liệu từ summary theo calculation_field
            records = self._get_data_from_summary(summary)
            
            if not records:
                return 0.0
            
            # Tạo context an toàn để thực thi công thức
            # Biến 'records' chứa danh sách records
            # Biến 'result' sẽ chứa kết quả cuối cùng
            safe_dict = {
                'records': records,
                'result': 0.0,
                # Math functions
                'math': math,
                'decimal': decimal,
                'statistics': statistics,
                'random': random,
                # Date/time functions
                'datetime': datetime,
                'date': date,
                'time': time,
                'timedelta': timedelta,
                'monthrange': monthrange,
                # String/Text functions
                're': re,
                'json': json,
                # Collection functions
                'collections': collections,
                'itertools': itertools,
                'operator': operator,
                'functools': functools,
                # Built-in functions
                '__builtins__': {
                    'abs': abs,
                    'min': min,
                    'max': max,
                    'round': round,
                    'sum': sum,
                    'len': len,
                    'sorted': sorted,
                    'reversed': reversed,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                    'any': any,
                    'all': all,
                    'bool': bool,
                    'int': int,
                    'float': float,
                    'str': str,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'range': range,
                }
            }
            
            # Thực thi công thức
            # Công thức sẽ sử dụng 'records' và gán kết quả vào 'result'
            exec(self.formula, safe_dict)
            
            # Lấy kết quả từ biến 'result'
            calculated_result = safe_dict.get('result', 0.0)
            
            # Đảm bảo kết quả là số
            if isinstance(calculated_result, (int, float)):
                return float(calculated_result)
            else:
                return 0.0
                
        except Exception as e:
            _logger.error(f"Error executing formula '{self.formula}' with summary_id {summary_id}: {str(e)}")
            return 0.0

    def _is_team_building_applicable_period(self, summary):
        try:
            month_int = int(summary.month)
            year_int = int(summary.year)
        except Exception:
            return False
        return year_int > 2026 or (year_int == 2026 and month_int >= 3)

    def _get_data_from_summary(self, summary):
        """
        Lấy dữ liệu từ summary theo calculation_field
        
        Args:
            summary: salary.sales.summary record
            
        Returns:
            list: Danh sách records hoặc dữ liệu để tính toán
        """
        self.ensure_one()
        
        if not self.calculation_field:
            # Nếu không có calculation_field, lấy tất cả detail lines
            return summary.line_ids.mapped('detail_line_ids')
        
        # Lấy dữ liệu theo calculation_field
        if self.calculation_field == 'total_line_ids':
            return summary.total_line_ids
        elif self.calculation_field == 'line_ids':
            return summary.line_ids
        elif self.calculation_field == 'detail_line_ids':
            return summary.line_ids.mapped('detail_line_ids')
        elif self.calculation_field == 'sales_commission_employee_ids':
            return summary.sales_commission_employee_ids
        elif self.calculation_field == 'humic_sales_detail_ids':
            return summary.humic_sales_detail_ids
        elif self.calculation_field == 'customer_open_list_ids':
            return summary.customer_open_list_ids
        elif self.calculation_field == 'commission_result_ids':
            return summary.commission_result_ids
        else:
            # Thử lấy field động từ summary
            if hasattr(summary, self.calculation_field):
                return getattr(summary, self.calculation_field)
            else:
                # Fallback về detail_line_ids
                return summary.line_ids.mapped('detail_line_ids')

    @api.model
    def calculate_all_commissions(self, summary_id):
        """
        Tính toán tất cả hoa hồng cho summary_id
        Nếu 1 type có nhiều record sẽ loop qua toàn bộ và sum kết quả
        
        Args:
            summary_id: ID của salary.sales.summary
            
        Returns:
            dict: Kết quả tính toán cho từng commission calculation
        """
        if not summary_id:
            return {}
        
        # Lấy tất cả calculations đang active
        calculations = self.search([])
        if not calculations:
            return {}
        
        results = {}
        
        # Group calculations by commission_type
        calculations_by_type = {}
        for calculation in calculations:
            commission_type = calculation.commission_type
            if commission_type not in calculations_by_type:
                calculations_by_type[commission_type] = []
            calculations_by_type[commission_type].append(calculation)
        
        # Process each type
        for commission_type, calc_list in calculations_by_type.items():
            total_amount = 0.0
            calculation_names = []
            
            # Loop through all calculations of the same type
            for calculation in calc_list:
                # Calculate commission for this specific calculation
                amount = calculation.calculate_commission(summary_id)
                total_amount += amount
                calculation_names.append(calculation.name)
                
                # Store individual result
                results[calculation.id] = {
                    'name': calculation.name,
                    'type': calculation.commission_type,
                    'amount': amount,
                    'currency': calculation.currency_id.symbol,
                    'is_individual': True
                }
            
            # Store combined result for this type
            if len(calc_list) > 1:
                combined_name = f"Tổng {commission_type} ({', '.join(calculation_names)})"
                results[f"combined_{commission_type}"] = {
                    'name': combined_name,
                    'type': commission_type,
                    'amount': total_amount,
                    'currency': calc_list[0].currency_id.symbol,
                    'is_combined': True,
                    'individual_calc_ids': [calc.id for calc in calc_list]
                }
        
        return results
