# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)

KEYS = ['debit', 'credit', 'balance', 'foreign_balance']

class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        lines = []
        date_from = fields.Date.from_string(options['date']['date_from'])
        company_currency = self.env.company.currency_id

        # Lấy thông tin currency để quyết định sử dụng NT hay không
        currency, currency_nt = self._get_selected_currency(options, company_currency, self.env['res.currency'])

        totals_by_column_group = defaultdict(lambda: {total: 0.0 for total in KEYS})
        for account, column_group_results in self._query_values(report, options):
            eval_dict = {}
            has_lines = False
            for column_group_key, results in column_group_results.items():
                account_sum = results.get('sum', {})
                account_un_earn = results.get('unaffected_earnings', {})

                account_debit = account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0)
                account_credit = account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0)
                account_balance = account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
                account_foreign_balance = account_sum.get('foreign_balance', 0.0) + account_un_earn.get('foreign_balance', 0.0)

                eval_dict[column_group_key] = {
                    'amount_currency': account_sum.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0),
                    'debit': account_debit,
                    'credit': account_credit,
                    'balance': account_balance,
                    'foreign_balance': account_foreign_balance,
                }

                max_date = account_sum.get('max_date')
                has_lines = has_lines or (max_date and max_date >= date_from)

                totals_by_column_group[column_group_key]['debit'] += account_debit
                totals_by_column_group[column_group_key]['credit'] += account_credit
                totals_by_column_group[column_group_key]['balance'] += account_balance
                totals_by_column_group[column_group_key]['foreign_balance'] += account_foreign_balance

            lines.append(self._get_account_title_line(report, options, account, has_lines, eval_dict))

        # Report total line.
        for totals in totals_by_column_group.values():
            totals['balance'] = company_currency.round(totals['balance'])
            totals['foreign_balance'] = company_currency.round(totals['foreign_balance'])

        # Tax Declaration lines.
        journal_options = report._get_options_journals(options)
        if len(options['column_groups']) == 1 and len(journal_options) == 1 and journal_options[0]['type'] in ('sale', 'purchase'):
            lines += self._tax_declaration_lines(report, options, journal_options[0]['type'])
        # Total line
        lines.append(self._get_total_line(report, options, totals_by_column_group))

        return [(0, line) for line in lines]

    def _get_aml_line(self, report, parent_line_id, options, eval_dict, init_bal_by_col_group):
        if eval_dict:
            # Đảm bảo foreign_balance có giá trị và đúng loại tiền tệ
            currency_env = self.env['res.currency']
            company_currency = self.env.company.currency_id
            selected_currency, selected_foreign_currency = self._get_selected_currency(options, company_currency, currency_env)
            
            # Nếu không có foreign_balance, sử dụng balance
            for col_group_key, values in eval_dict.items():
                if 'foreign_balance' not in values or values.get('foreign_balance') is None:
                    values['foreign_balance'] = values.get('balance', 0.0)
        
        # Chuyển đổi init_bal_by_col_group từ dict phức tạp sang dict đơn giản cho method gốc
        simple_init_bal = {}
        for col_group_key, value in init_bal_by_col_group.items():
            if isinstance(value, dict):
                # Lấy balance value cho method gốc
                simple_init_bal[col_group_key] = value.get('balance', 0.0)
            else:
                simple_init_bal[col_group_key] = value
        
        res = super(GeneralLedgerCustomHandler, self)._get_aml_line(report, parent_line_id, options, eval_dict, simple_init_bal)
        
        # Xử lý lũy tiến cho balance và foreign_balance
        for i, column in enumerate(options['columns']):
            col_expr_label = column['expression_label']
            if col_expr_label in ['balance', 'foreign_balance']:
                if col_expr_label == 'balance':
                    col_value = eval_dict.get(column['column_group_key'], {}).get('balance', 0.0)
                else:  # foreign_balance
                    col_value = eval_dict.get(column['column_group_key'], {}).get('foreign_balance', 0.0)
                
                if col_value is not None:
                    # Cộng dồn với initial balance
                    init_balance = init_bal_by_col_group.get(column['column_group_key'], 0.0)
                    if isinstance(init_balance, dict):
                        init_balance = init_balance.get(col_expr_label, 0.0)
                    col_value += init_balance
                    
                    # Cập nhật giá trị trong columns
                    if i < len(res['columns']):
                        res['columns'][i]['no_format'] = col_value
                        
                        # Format lại giá trị
                        if col_expr_label == 'balance':
                            # Format balance với currency chính
                            currency_env = self.env['res.currency']
                            company_currency = self.env.company.currency_id
                            selected_currency, selected_foreign_currency = self._get_selected_currency(options, company_currency, currency_env)
                            res['columns'][i]['name'] = selected_currency.format(col_value)
                        else:  # foreign_balance
                            # Format foreign_balance với currency ngoại tệ
                            currency_env = self.env['res.currency']
                            company_currency = self.env.company.currency_id
                            selected_currency, selected_foreign_currency = self._get_selected_currency(options, company_currency, currency_env)
                            res['columns'][i]['name'] = selected_foreign_currency.format(col_value)
        
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
        report = self.env.ref('account_reports.general_ledger_report')
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

    def _get_query_sums(self, report, options):
        """ Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all accounts.
        - sums for the initial balances.
        - sums for the unaffected earnings.
        - sums for the tax declaration.
        :return:                    (query, params)
        """
        # Lấy thông tin currency từ options
        currency_env = self.env['res.currency']
        company_currency = self.env.company.currency_id
        currency, currency_nt = self._get_selected_currency(options, company_currency, currency_env)
        
        options_by_column_group = report._split_options_per_column_group(options)

        params = []
        queries = []

        # Create the currency table.
        # As the currency table is the same whatever the comparisons, create it only once.
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        # ============================================
        # 1) Get sums for all accounts.
        # ============================================
        for column_group_key, options_group in options_by_column_group.items():
            if not options.get('general_ledger_strict_range'):
                options_group = self._get_options_sum_balance(options_group)

            # Sum is computed including the initial balance of the accounts configured to do so, unless a special option key is used
            # (this is required for trial balance, which is based on general ledger)
            sum_date_scope = 'strict_range' if options_group.get('general_ledger_strict_range') else 'normal'

            query_domain = []

            if options.get('filter_search_bar'):
                query_domain.append(('account_id', 'ilike', options['filter_search_bar']))

            if options_group.get('include_current_year_in_unaff_earnings'):
                query_domain += [('account_id.include_initial_balance', '=', True)]

            tables, where_clause, where_params = report._query_get(options_group, sum_date_scope, domain=query_domain)
            params.append(column_group_key)
            
            # Tính foreign_balance dựa trên currency_nt
            # Nếu aml.currency_id = company.currency_id thì foreign_balance = 0
            if currency_nt != company_currency:
                foreign_balance_expr = f'SUM(CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.amount_currency END)'
            else:
                foreign_balance_expr = f'SUM(CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) END)'
            
            params += where_params
            
            queries.append(f"""
                SELECT
                    account_move_line.account_id                            AS groupby,
                    'sum'                                                   AS key,
                    MAX(account_move_line.date)                             AS max_date,
                    %s                                                      AS column_group_key,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance,
                    {foreign_balance_expr} AS foreign_balance
                FROM {tables}
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                GROUP BY account_move_line.account_id
            """)

        return ' UNION ALL '.join(queries), params

    def _get_query_amls(self, report, options, expanded_account_ids, offset=0, limit=None):
        """ Construct a query retrieving all the account move lines to build the report.
        :return:                    (query, params)
        """
        # Lấy thông tin currency từ options
        currency_env = self.env['res.currency']
        company_currency = self.env.company.currency_id
        currency, currency_nt = self._get_selected_currency(options, company_currency, currency_env)
        
        options_by_column_group = report._split_options_per_column_group(options)

        params = []
        queries = []

        # Create the currency table.
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        for column_group_key, options_group in options_by_column_group.items():
            if not options.get('general_ledger_strict_range'):
                options_group = self._get_options_sum_balance(options_group)

            # Sum is computed including the initial balance of the accounts configured to do so, unless a special option key is used
            # (this is required for trial balance, which is based on general ledger)
            sum_date_scope = 'strict_range' if options_group.get('general_ledger_strict_range') else 'normal'

            query_domain = [('account_id', 'in', expanded_account_ids)]

            if options.get('filter_search_bar'):
                query_domain.append(('account_id', 'ilike', options['filter_search_bar']))

            tables, where_clause, where_params = report._query_get(options_group, sum_date_scope, domain=query_domain)
            params.append(column_group_key)
            
            # Tính foreign_balance dựa trên currency_nt
            # Nếu aml.currency_id = company.currency_id thì foreign_balance = 0
            if currency_nt != company_currency:
                foreign_balance_expr = f'CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.amount_currency END'
            else:
                foreign_balance_expr = f'CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) END'
            
            params += where_params
            
            queries.append(f"""
                SELECT
                    account_move_line.id,
                    account_move_line.date,
                    account_move_line.date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    account_move_line.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    account_move_line.matching_number,
                    ROUND(account_move_line.debit * currency_table.rate, currency_table.precision) AS debit,
                    ROUND(account_move_line.credit * currency_table.rate, currency_table.precision) AS credit,
                    ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                    {foreign_balance_expr} AS foreign_balance,
                    account_move.name                                                                AS move_name,
                    account_move.move_type                                                           AS move_type,
                    account.code                                                                     AS account_code,
                    account.name                                                                     AS account_name,
                    journal.code                                                                     AS journal_code,
                    journal.name                                                                     AS journal_name,
                    %s                                                                               AS column_group_key
                FROM {tables}
                JOIN account_move ON account_move.id = account_move_line.move_id
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN account_account account           ON account.id = account_move_line.account_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                WHERE {where_clause}
                ORDER BY account_move_line.date, account_move_line.id
            """)

        query = '(' + ') UNION ALL ('.join(queries) + ')'

        if offset:
            query += ' OFFSET %s '
            params.append(offset)
        if limit:
            query += ' LIMIT %s '
            params.append(limit)

        return query, params