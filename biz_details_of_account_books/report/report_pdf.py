# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

 
class rp_detail_book_pdf(models.AbstractModel):
    _name = 'report.biz_details_of_account_books.rp_detail_book_pdf'
    _description = 'rp_detail_book_pdf'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        doc = self.env['detail.book.account'].browse(docids)
        options = data
        # options = {'context': {'lang': 'vi_VN', 'tz': 'Asia/Saigon', 'uid': 2, 'allowed_company_ids': [1], 'params': {'cids': 1, 'menu_id': 376, 'action': 2057}, 'report_id': 50}, 'unfolded_lines': [], 'available_variants': [{'id': 50, 'name': 'Sổ chi tiết các tài khoản BTC (S38-DN)', 'country_id': False}], 'report_id': 50, 'allow_domestic': True, 'fiscal_position': 'all', 'available_vat_fiscal_positions': [], 'date': {'string': '2023', 'period_type': 'fiscalyear', 'mode': 'range', 'date_from': '2023-01-01', 'date_to': '2023-12-31', 'filter': 'this_year'}, 'available_horizontal_groups': [], 'selected_horizontal_group_id': None, 'account': True, 'account_ids': [], 'selected_account_ids': [], 'all_entries': False, 'analytic': True, 'analytic_accounts': [], 'selected_analytic_account_names': [], 'buttons': [{'name': 'PDF', 'sequence': 1, 'action': 'acction_print_pdf', 'file_export_type': 'PDF'}, {'name': 'XLSX', 'sequence': 20, 'action': 'export_file', 'action_param': 'export_to_xlsx', 'file_export_type': 'XLSX'}, {'name': 'Lưu', 'sequence': 100, 'action': 'open_report_export_wizard'}], 'journals': [{'id': 7, 'model': 'account.journal', 'name': 'Bank', 'title': 'Bank - BNK1', 'selected': False, 'type': 'bank'}, {'id': 6, 'model': 'account.journal', 'name': 'Cash', 'title': 'Cash - CSH1', 'selected': False, 'type': 'cash'}, {'id': 5, 'model': 'account.journal', 'name': 'Cash Basis Taxes', 'title': 'Cash Basis Taxes - CABA', 'selected': False, 'type': 'cash'}, {'id': 18, 'model': 'account.journal', 'name': 'Chi phí', 'title': 'Chi phí - EXP', 'selected': False, 'type': 'purchase'}, {'id': 1, 'model': 'account.journal', 'name': 'Customer Invoices', 'title': 'Customer Invoices - INV', 'selected': False, 'type': 'sale'}, {'id': 4, 'model': 'account.journal', 'name': 'Exchange Difference', 'title': 'Exchange Difference - EXCH', 'selected': False, 'type': 'bank'}, {'id': 10, 'model': 'account.journal', 'name': 'IFRS Automatic Transfers', 'title': 'IFRS Automatic Transfers - IFRS', 'selected': False, 'type': 'general'}, {'id': 3, 'model': 'account.journal', 'name': 'Miscellaneous Operations', 'title': 'Miscellaneous Operations - MISC', 'selected': False, 'type': 'general'}, {'id': 21, 'model': 'account.journal', 'name': 'Point of Sale', 'title': 'Point of Sale - POSS', 'selected': False, 'type': 'general'}, {'id': 9, 'model': 'account.journal', 'name': 'Salaries', 'title': 'Salaries - SLR', 'selected': False, 'type': 'general'}, {'id': 2, 'model': 'account.journal', 'name': 'Vendor Bills', 'title': 'Vendor Bills - BILL', 'selected': False, 'type': 'purchase'}, {'id': 20, 'model': 'account.journal', 'name': 'Định giá tồn kho', 'title': 'Định giá tồn kho - STJ', 'selected': False, 'type': 'general'}], 'name_journal_group': 'Tất cả bút toán', 'partner': True, 'partner_ids': [], 'partner_categories': [], 'selected_partner_ids': [], 'selected_partner_categories': [], 'unreconciled': False, 'search_bar': True, 'unfold_all': False, 'column_headers': [[{'name': '2023', 'forced_options': {'date': {'string': '2023', 'period_type': 'fiscalyear', 'mode': 'range', 'date_from': '2023-01-01', 'date_to': '2023-12-31', 'filter': 'this_year'}}}]], 'columns': [{'name': 'Ngày tháng ghi sổ', 'column_group_key': "(('forced_options', (('date', (('date_from', '2023-01-01'), ('date_to', '2023-12-31'), ('filter', 'this_year'), ('mode', 'range'), ('period_type', 'fiscalyear'), ('string', '2023'))),)), ('horizontal_groupby_element', ()))", 'expression_label': 'date_numbered', 'sortable': False, 'figure_type': 'none', 'blank_if_zero': True, 'style': 'text-align: center; white-space: nowrap;'}, {'name': 'Số hiệu', 'column_group_key': "(('forced_options', (('date', (('date_from', '2023-01-01'), ('date_to', '2023-12-31'), ('filter', 'this_year'), ('mode', 'range'), ('period_type', 'fiscalyear'), ('string', '2023'))),)), ('horizontal_groupby_element', ()))", 'expression_label': 'number', 'sortable': False, 'figure_type': 'none', 'blank_if_zero': True, 'style': 'text-align: center; white-space: nowrap;'}, {'name': 'Ngày', 'column_group_key': "(('forced_options', (('date', (('date_from', '2023-01-01'), ('date_to', '2023-12-31'), ('filter', 'this_year'), ('mode', 'range'), ('period_type', 'fiscalyear'), ('string', '2023'))),)), ('horizontal_groupby_element', ()))", 'expression_label': 'date', 'sortable': False, 'figure_type': 'none', 'blank_if_zero': True, 'style': 'text-align: center; white-space: nowrap;'}, {'name': 'Diễn giải', 'column_group_key': "(('forced_options', (('date', (('date_from', '2023-01-01'), ('date_to', '2023-12-31'), ('filter', 'this_year'), ('mode', 'range'), ('period_type', 'fiscalyear'), ('string', '2023'))),)), ('horizontal_groupby_element', ()))", 'expression_label': 'explain', 'sortable': False, 'figure_type': 'none', 'blank_if_zero': True, 'style': 'text-align: center; white-space: nowrap;'}, {'name': 'TK đối ứng', 'column_group_key': "(('forced_options', (('date', (('date_from', '2023-01-01'), ('date_to', '2023-12-31'), ('filter', 'this_year'), ('mode', 'range'), ('period_type', 'fiscalyear'), ('string', '2023'))),)), ('horizontal_groupby_element', ()))", 'expression_label': 'countered_accounts', 'sortable': False, 'figure_type': 'none', 'blank_if_zero': True, 'style': 'text-align: center; white-space: nowrap;'}, {'name': 'Nợ', 'column_group_key': "(('forced_options', (('date', (('date_from', '2023-01-01'), ('date_to', '2023-12-31'), ('filter', 'this_year'), ('mode', 'range'), ('period_type', 'fiscalyear'), ('string', '2023'))),)), ('horizontal_groupby_element', ()))", 'expression_label': 'debit', 'sortable': False, 'figure_type': 'monetary', 'blank_if_zero': True, 'style': 'text-align: center; white-space: nowrap;'}, {'name': 'Có', 'column_group_key': "(('forced_options', (('date', (('date_from', '2023-01-01'), ('date_to', '2023-12-31'), ('filter', 'this_year'), ('mode', 'range'), ('period_type', 'fiscalyear'), ('string', '2023'))),)), ('horizontal_groupby_element', ()))", 'expression_label': 'credit', 'sortable': False, 'figure_type': 'monetary', 'blank_if_zero': True, 'style': 'text-align: center; white-space: nowrap;'}, {'name': 'Số dư', 'column_group_key': "(('forced_options', (('date', (('date_from', '2023-01-01'), ('date_to', '2023-12-31'), ('filter', 'this_year'), ('mode', 'range'), ('period_type', 'fiscalyear'), ('string', '2023'))),)), ('horizontal_groupby_element', ()))", 'expression_label': 'balance', 'sortable': False, 'figure_type': 'monetary', 'blank_if_zero': True, 'style': 'text-align: center; white-space: nowrap;'}], 'column_groups': {"(('forced_options', (('date', (('date_from', '2023-01-01'), ('date_to', '2023-12-31'), ('filter', 'this_year'), ('mode', 'range'), ('period_type', 'fiscalyear'), ('string', '2023'))),)), ('horizontal_groupby_element', ()))": {'forced_options': {'date': {'string': '2023', 'period_type': 'fiscalyear', 'mode': 'range', 'date_from': '2023-01-01', 'date_to': '2023-12-31', 'filter': 'this_year'}}, 'forced_domain': []}}, 'show_debug_column': False, 'show_growth_comparison': None, 'order_column': None, 'hierarchy': False, 'display_hierarchy_filter': False, 'unposted_in_period': True, 'report_type': 'pdf'}

        report_id = self.env['account.report'].browse(int(options['report_id']))
       
        from_date = options['date']['date_from'] if options.get('date') and options['date'].get('date_from') else ''
        to_date = options['date']['date_to'] if options.get('date') and options['date'].get('date_to') else ''
        
        from_date = options['date']['date_from'] if options.get('date') and options['date'].get('date_from') else ''
        to_date = options['date']['date_to'] if options.get('date') and options['date'].get('date_to') else ''
        
        if from_date:
            from_date_date = datetime.strptime(from_date, "%Y-%m-%d")
            from_date = from_date_date.strftime('%d/%m/%Y')
        if to_date:
            to_date_date = datetime.strptime(to_date, "%Y-%m-%d")
            to_date = to_date_date.strftime('%d/%m/%Y')
        
        sub_title = 'Từ ngày %s đến ngày %s' % (from_date, to_date)

        print_mode_self = report_id.with_context(no_format=True, print_mode=True, prefetch_fields=False)
        print_options = print_mode_self._get_options(previous_options=options)
        lines = report_id._filter_out_folded_children(print_mode_self._get_lines(print_options))
        
        res = doc.get_format_data_lines(report_id,lines)
        return {
            'doc_ids': docids,
            'doc':doc,
            'get_company_address': doc.get_company_address,
            'sub_title': sub_title,
            'get_accounts': doc._get_accounts(options),
            'get_partners': doc._get_partners(options),
            'lines': res,
            'doc_model': 'detail.book.account',
        }