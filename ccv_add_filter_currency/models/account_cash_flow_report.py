# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools.misc import get_lang

import logging
_logger = logging.getLogger(__name__)

KEYS = ['debit', 'credit', 'balance', 'foreign_balance']

class CashFlowReportCustomHandler(models.AbstractModel):
    _inherit = 'account.cash.flow.report.handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        # Compute the cash flow report using the direct method: https://www.investopedia.com/terms/d/direct_method.asp
        lines = []

        # Lấy thông tin currency để quyết định sử dụng NT hay không
        company_currency = self.env.company.currency_id
        currency, currency_nt = self._get_selected_currency(options, company_currency, self.env['res.currency'])

        layout_data = self._get_layout_data()
        report_data = self._get_report_data(report, options, layout_data)

        for layout_line_id, layout_line_data in layout_data.items():
            lines.append((0, self._get_layout_line(report, options, layout_line_id, layout_line_data, report_data)))

            if layout_line_id in report_data and 'aml_groupby_account' in report_data[layout_line_id]:
                for aml_data in report_data[layout_line_id]['aml_groupby_account'].values():
                    lines.append((0, self._get_aml_line(report, options, aml_data)))

        unexplained_difference_line = self._get_unexplained_difference_line(report, options, report_data)

        if unexplained_difference_line:
            lines.append((0, unexplained_difference_line))

        return lines

    def _get_report_data(self, report, options, layout_data):
        res = super(CashFlowReportCustomHandler, self)._get_report_data(report, options, layout_data)
        
        # Lấy thông tin currency để quyết định sử dụng NT hay không
        company_currency = self.env.company.currency_id
        currency, currency_nt = self._get_selected_currency(options, company_currency, self.env['res.currency'])
        
        for key in res.keys():
            balance = res[key].get('balance', False)
            if balance:
                # Tính foreign_balance dựa trên currency_nt
                if currency_nt != company_currency:
                    # Sử dụng amount_currency nếu có, nếu không thì dùng balance
                    foreign_balance = res[key].get('amount_currency', balance)
                else:
                    foreign_balance = balance
                res[key].update({'foreign_balance': foreign_balance})
        return res

    def _get_aml_line(self, report, options, aml_data):
        if aml_data:
            # Lấy thông tin currency để quyết định sử dụng NT hay không
            company_currency = self.env.company.currency_id
            currency, currency_nt = self._get_selected_currency(options, company_currency, self.env['res.currency'])
            
            # Tính foreign_balance dựa trên currency_nt
            if currency_nt != company_currency:
                foreign_balance = aml_data.get('amount_currency', aml_data.get('balance', 0.0))
            else:
                foreign_balance = aml_data.get('balance', 0.0)
            aml_data.update({'foreign_balance': foreign_balance})
            
        res = super(CashFlowReportCustomHandler, self)._get_aml_line(report, options, aml_data)
        
        # Format currency columns
        res = self._format_currency_columns(res, options)
        
        return res

    def _format_currency_columns(self, line_result, options):
        """Format currency columns for a line result"""
        if not line_result or 'columns' not in line_result:
            return line_result
            
        # Get currency settings
        currency_env = self.env['res.currency']
        company_currency = self.env.company.currency_id
        selected_currency, selected_foreign_currency = self._get_selected_currency(options, company_currency, currency_env)
        
        # Get column indices from report
        report = self.env.ref('account_reports.cash_flow_report')
        monetary_columns, currency_columns, foreign_currency_columns = report._identify_currency_indices(options)
        
        if not (currency_columns or foreign_currency_columns):
            return line_result
            
        # Format columns
        columns = line_result['columns']
        for col_index, column in enumerate(columns):
            if col_index in currency_columns and column.get('no_format') is not None:
                # Format with selected currency
                no_format_value = float(column['no_format']) if isinstance(column['no_format'], (int, float)) else 0.0
                column['name'] = selected_currency.format(no_format_value)
                column['no_format'] = no_format_value
            elif col_index in foreign_currency_columns and column.get('no_format') is not None:
                # Format with selected foreign currency
                no_format_value = float(column['no_format']) if isinstance(column['no_format'], (int, float)) else 0.0
                column['name'] = selected_foreign_currency.format(no_format_value)
                column['no_format'] = no_format_value
                
        return line_result

    def _get_selected_currency(self, options, company_currency, currency_env):
        """Lấy currency được chọn từ options"""
        currency_id = None
        currency_nt_id = None
        
        # Lấy currency chính từ currency_options
        if options.get('currency_options'):
            for currency_option in options['currency_options']:
                if currency_option.get('selected'):
                    currency_id = currency_option.get('id')
                    break
        
        # Lấy currency ngoại tệ từ currency_nt_options  
        if options.get('currency_nt_options'):
            for currency_nt_option in options['currency_nt_options']:
                if currency_nt_option.get('selected'):
                    currency_nt_id = currency_nt_option.get('id')
                    break
        
        currency = currency_env.browse(currency_id) if currency_id else company_currency
        currency_nt = currency_env.browse(currency_nt_id) if currency_nt_id else company_currency
        
        return currency, currency_nt

    def _compute_liquidity_balance(self, report, options, currency_table_query, payment_account_ids, date_scope):
        ''' Compute the balance of all liquidity accounts to populate the following sections:
            'Cash and cash equivalents, beginning of period' and 'Cash and cash equivalents, closing balance'.

        :param options:                 The report options.
        :param currency_table_query:    The custom query containing the multi-companies rates.
        :param payment_account_ids:     A tuple containing all account.account's ids being used in a liquidity journal.
        :return:                        A list of tuple (account_id, account_code, account_name, balance).
        '''
        # Lấy thông tin currency từ options
        company_currency = self.env.company.currency_id
        currency, currency_nt = self._get_selected_currency(options, company_currency, self.env['res.currency'])
        
        queries = []
        params = []
        if self.pool['account.account'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            account_name = f"COALESCE(account_account.name->>'{lang}', account_account.name->>'en_US')"
        else:
            account_name = 'account_account.name'

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            tables, where_clause, where_params = report._query_get(column_group_options, date_scope, domain=[('account_id', 'in', payment_account_ids)])

            # Tính foreign_balance dựa trên currency_nt
            # Nếu aml.currency_id = company.currency_id thì foreign_balance = 0
            if currency_nt != company_currency:
                foreign_balance_expr = f'SUM(CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.amount_currency END)'
            else:
                foreign_balance_expr = f'SUM(CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) END)'
            
            params += where_params

            queries.append(f'''
                SELECT
                    %s AS column_group_key,
                    account_move_line.account_id,
                    account_account.code AS account_code,
                    {account_name} AS account_name,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance,
                    {foreign_balance_expr} AS foreign_balance
                FROM {tables}
                JOIN account_account
                    ON account_account.id = account_move_line.account_id
                LEFT JOIN {currency_table_query}
                    ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                GROUP BY account_move_line.account_id, account_account.code, {account_name}
            ''')

            params += [column_group_key, *where_params]

        self._cr.execute(' UNION ALL '.join(queries), params)

        return self._cr.dictfetchall()

    def _get_liquidity_moves(self, report, options, currency_table_query, payment_account_ids, payment_move_ids, cash_flow_tag_ids):
        ''' Fetch all information needed to compute lines from liquidity moves.
        The difficulty is to represent only the not-reconciled part of balance.

        :param options:                 The report options.
        :param currency_table_query:    The floating query to handle a multi-company/multi-currency environment.
        :param payment_move_ids:        A tuple containing all account.move's ids being the liquidity moves.
        :param payment_account_ids:     A tuple containing all account.account's ids being used in a liquidity journal.
        :param cash_flow_tag_ids:       A tuple containing all account.account.tag's ids being used in a cash flow report.
        :return:                        A list of tuple (account_id, account_code, account_name, balance).
        '''
        # Lấy thông tin currency từ options
        company_currency = self.env.company.currency_id
        currency, currency_nt = self._get_selected_currency(options, company_currency, self.env['res.currency'])
        
        queries = []
        params = []
        if self.pool['account.account'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            account_name = f"COALESCE(account_account.name->>'{lang}', account_account.name->>'en_US')"
        else:
            account_name = 'account_account.name'

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            tables, where_clause, where_params = report._query_get(column_group_options, 'strict_range', domain=[('account_id', 'in', payment_account_ids), ('move_id', 'in', payment_move_ids)])

            # Tính foreign_balance dựa trên currency_nt
            # Nếu aml.currency_id = company.currency_id thì foreign_balance = 0
            if currency_nt != company_currency:
                foreign_balance_expr = f'SUM(CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.amount_currency END)'
            else:
                foreign_balance_expr = f'SUM(CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) END)'
            
            # Thêm company_currency.id vào params trước where_params
            params.append(company_currency.id)
            params += where_params

            queries.append(f'''
                SELECT
                    %s AS column_group_key,
                    account_move_line.account_id,
                    account_account.code AS account_code,
                    {account_name} AS account_name,
                    account_account.account_type AS account_account_type,
                    account_account_tag.id AS account_tag_id,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance,
                    {foreign_balance_expr} AS foreign_balance
                FROM {tables}
                JOIN account_account
                    ON account_account.id = account_move_line.account_id
                LEFT JOIN account_account_account_tag_rel
                    ON account_account_account_tag_rel.account_account_id = account_account.id
                LEFT JOIN account_account_tag
                    ON account_account_tag.id = account_account_account_tag_rel.account_account_tag_id
                LEFT JOIN {currency_table_query}
                    ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                GROUP BY account_move_line.account_id, account_account.code, {account_name}, account_account.account_type, account_account_tag.id
            ''')

            params += [column_group_key, *where_params]

        self._cr.execute(' UNION ALL '.join(queries), params)

        return self._cr.dictfetchall()

    def _get_reconciled_moves(self, report, options, currency_table_query, payment_account_ids, payment_move_ids, cash_flow_tag_ids):
        ''' Fetch all information needed to compute lines from reconciled moves.
        The difficulty is to represent only the reconciled part of balance.

        :param options:                 The report options.
        :param currency_table_query:    The floating query to handle a multi-company/multi-currency environment.
        :param payment_move_ids:        A tuple containing all account.move's ids being the liquidity moves.
        :param payment_account_ids:     A tuple containing all account.account's ids being used in a liquidity journal.
        :param cash_flow_tag_ids:       A tuple containing all account.account.tag's ids being used in a cash flow report.
        :return:                        A list of tuple (account_id, account_code, account_name, balance).
        '''
        # Lấy thông tin currency từ options
        company_currency = self.env.company.currency_id
        currency, currency_nt = self._get_selected_currency(options, company_currency, self.env['res.currency'])
        
        queries = []
        params = []
        if self.pool['account.account'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            account_name = f"COALESCE(account_account.name->>'{lang}', account_account.name->>'en_US')"
        else:
            account_name = 'account_account.name'

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            tables, where_clause, where_params = report._query_get(column_group_options, 'strict_range', domain=[('account_id', 'in', payment_account_ids), ('move_id', 'not in', payment_move_ids)])

            # Tính foreign_balance dựa trên currency_nt
            # Nếu aml.currency_id = company.currency_id thì foreign_balance = 0
            if currency_nt != company_currency:
                foreign_balance_expr = 'SUM(CASE WHEN account_move_line.currency_id = %s THEN 0 ELSE account_move_line.amount_currency END)'
            else:
                foreign_balance_expr = 'SUM(CASE WHEN account_move_line.currency_id = %s THEN 0 ELSE ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) END)'
            
            # Thêm company_currency.id vào params trước where_params
            params.append(company_currency.id)
            params += where_params

            queries.append(f'''
                SELECT
                    %s AS column_group_key,
                    account_move_line.account_id,
                    account_account.code AS account_code,
                    {account_name} AS account_name,
                    account_account.account_type AS account_account_type,
                    account_account_tag.id AS account_tag_id,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance,
                    {foreign_balance_expr} AS foreign_balance
                FROM {tables}
                JOIN account_account
                    ON account_account.id = account_move_line.account_id
                LEFT JOIN account_account_account_tag_rel
                    ON account_account_account_tag_rel.account_account_id = account_account.id
                LEFT JOIN account_account_tag
                    ON account_account_tag.id = account_account_account_tag_rel.account_account_tag_id
                LEFT JOIN {currency_table_query}
                    ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                GROUP BY account_move_line.account_id, account_account.code, {account_name}, account_account.account_type, account_account_tag.id
            ''')

            params += [column_group_key, *where_params]

        self._cr.execute(' UNION ALL '.join(queries), params)

        return self._cr.dictfetchall()