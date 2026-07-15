import json
import logging

from collections import defaultdict
from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang

_logger = logging.getLogger(__name__)

KEYS = ['debit', 'credit', 'balance', 'foreign_balance']

class PartnerLedger(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    def _build_partner_lines(self, report, options, level_shift=0):
        lines = []

        # Lấy thông tin currency để quyết định sử dụng NT hay không
        company_currency = self.env.company.currency_id
        currency, currency_nt = self._get_selected_currency(options, company_currency, self.env['res.currency'])

        totals_by_column_group = {
            column_group_key: { total: 0.0 for total in KEYS }
            for column_group_key in options['column_groups']
        }

        for partner, results in self._query_partners(options):
            partner_values = defaultdict(dict)

            for column_group_key in options['column_groups']:
                partner_sum = results.get(column_group_key, {})
                
                # Sử dụng foreign_balance từ query
                foreign_balance = partner_sum.get('foreign_balance', 0.0)
                partner_sum['foreign_balance'] = foreign_balance
                
                for key in KEYS:
                    partner_values[column_group_key][key] = partner_sum.get(key, 0.0)
                    totals_by_column_group[column_group_key][key] += partner_values[column_group_key][key]

            lines.append(self._get_report_line_partners(options, partner, partner_values, level_shift=level_shift))
        return lines, totals_by_column_group

    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        # Lấy thông tin currency từ options
        currency_env = self.env['res.currency']
        company_currency = self.env.company.currency_id
        currency, currency_nt = self._get_selected_currency(options, company_currency, currency_env)

        rslt = {partner_id: [] for partner_id in partner_ids}

        partner_ids_wo_none = [x for x in partner_ids if x]
        directly_linked_aml_partner_clauses = []
        directly_linked_aml_partner_params = []
        indirectly_linked_aml_partner_params = []
        indirectly_linked_aml_partner_clause = 'aml_with_partner.partner_id IS NOT NULL'
        if None in partner_ids:
            directly_linked_aml_partner_clauses.append('account_move_line.partner_id IS NULL')
        if partner_ids_wo_none:
            directly_linked_aml_partner_clauses.append('account_move_line.partner_id IN %s')
            directly_linked_aml_partner_params.append(tuple(partner_ids_wo_none))
            indirectly_linked_aml_partner_clause = 'aml_with_partner.partner_id IN %s'
            indirectly_linked_aml_partner_params.append(tuple(partner_ids_wo_none))
        directly_linked_aml_partner_clause = '(' + ' OR '.join(directly_linked_aml_partner_clauses) + ')'

        ct_query = self.env['res.currency']._get_query_currency_table(options)
        queries = []
        all_params = []
        lang = self.env.lang or get_lang(self.env).code
        journal_name = f"COALESCE(journal.name->>'{lang}', journal.name->>'en_US')" if \
            self.pool['account.journal'].name.translate else 'journal.name'
        account_name = f"COALESCE(account.name->>'{lang}', account.name->>'en_US')" if \
            self.pool['account.account'].name.translate else 'account.name'
        report = self.env.ref('account_reports.partner_ledger_report')
        for column_group_key, group_options in report._split_options_per_column_group(options).items():
            tables, where_clause, where_params = report._query_get(group_options, 'strict_range')

            all_params += [
                column_group_key,
                *where_params,
                *directly_linked_aml_partner_params,
                column_group_key,
                *indirectly_linked_aml_partner_params,
                *where_params,
                group_options['date']['date_from'],
                group_options['date']['date_to'],
            ]

            # For the move lines directly linked to this partner
            # Tính foreign_balance dựa trên currency_nt
            # Nếu aml.currency_id = company.currency_id thì foreign_balance = 0
            if currency_nt != company_currency:
                foreign_balance_expr = f'CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.amount_currency END'
            else:
                foreign_balance_expr = f'CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.balance END'
                
            queries.append(f'''
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
                    CASE WHEN account_move_line.debit = 0 THEN 0 ELSE {'account_move_line.debit' if currency == company_currency else 'abs(account_move_line.amount_currency)'} END AS debit,
                    CASE WHEN account_move_line.credit = 0 THEN 0 ELSE {'account_move_line.credit' if currency == company_currency else 'abs(account_move_line.amount_currency)'} END AS credit,
                    {'account_move_line.balance' if currency == company_currency else 'abs(account_move_line.amount_currency)'} AS balance,
                    {foreign_balance_expr} AS foreign_balance,
                    account_move.name                                                                AS move_name,
                    account_move.move_type                                                           AS move_type,
                    account.code                                                                     AS account_code,
                    {account_name}                                                                   AS account_name,
                    journal.code                                                                     AS journal_code,
                    {journal_name}                                                                   AS journal_name,
                    %s                                                                               AS column_group_key,
                    'directly_linked_aml'                                                            AS key
                FROM {tables}
                JOIN account_move ON account_move.id = account_move_line.move_id
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN account_account account           ON account.id = account_move_line.account_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                WHERE {where_clause} AND {directly_linked_aml_partner_clause}
                ORDER BY account_move_line.date, account_move_line.id
            ''')

            # For the move lines linked to no partner, but reconciled with this partner. They will appear in grey in the report
            # Tính foreign_balance dựa trên currency_nt cho indirectly linked
            # Nếu aml.currency_id = company.currency_id thì foreign_balance = 0
            if currency_nt != company_currency:
                foreign_balance_expr_indirect = f'CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.amount_currency END'
            else:
                foreign_balance_expr_indirect = f'CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.balance END'
                
            queries.append(f'''
                SELECT
                    account_move_line.id,
                    account_move_line.date,
                    account_move_line.date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    aml_with_partner.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    account_move_line.matching_number,
                    CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE {'account_move_line.debit' if currency == company_currency else 'abs(account_move_line.amount_currency)'} END AS debit, 
                    CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE {'account_move_line.credit' if currency == company_currency else 'abs(account_move_line.amount_currency)'} END AS credit,
                    - sign(aml_with_partner.balance) * {'account_move_line.balance' if currency == company_currency else 'abs(account_move_line.amount_currency)'} AS balance,
                    - sign(aml_with_partner.balance) * {foreign_balance_expr_indirect} AS foreign_balance,
                    account_move.name                                                                   AS move_name,
                    account_move.move_type                                                              AS move_type,
                    account.code                                                                        AS account_code,
                    {account_name}                                                                      AS account_name,
                    journal.code                                                                        AS journal_code,
                    {journal_name}                                                                      AS journal_name,
                    %s                                                                                  AS column_group_key,
                    'indirectly_linked_aml'                                                             AS key
                FROM {tables}
                    LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id,
                    account_partial_reconcile partial,
                    account_move,
                    account_move_line aml_with_partner,
                    account_journal journal,
                    account_account account
                WHERE
                    (account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id)
                    AND account_move_line.partner_id IS NULL
                    AND account_move.id = account_move_line.move_id
                    AND (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
                    AND {indirectly_linked_aml_partner_clause}
                    AND journal.id = account_move_line.journal_id
                    AND account.id = account_move_line.account_id
                    AND {where_clause}
                    AND partial.max_date BETWEEN %s AND %s
                ORDER BY account_move_line.date, account_move_line.id
            ''')

        query = '(' + ') UNION ALL ('.join(queries) + ')'

        if offset:
            query += ' OFFSET %s '
            all_params.append(offset)
        if limit:
            query += ' LIMIT %s '
            all_params.append(limit)

        self._cr.execute(query, all_params)
        for result in self._cr.dictfetchall():
            rslt[result['partner_id']].append(result)
        return rslt

    def _get_report_line_move_line(self, options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=0):
        if aml_query_result:
            # Đảm bảo foreign_balance có giá trị và đúng loại tiền tệ
            currency_env = self.env['res.currency']
            company_currency = self.env.company.currency_id
            selected_currency, selected_foreign_currency = self._get_selected_currency(options, company_currency, currency_env)
            
            # Nếu không có foreign_balance, sử dụng balance
            if 'foreign_balance' not in aml_query_result or aml_query_result.get('foreign_balance') is None:
                aml_query_result['foreign_balance'] = aml_query_result.get('balance', 0.0)
        
        # Chuyển đổi init_bal_by_col_group từ dict phức tạp sang dict đơn giản cho method gốc
        simple_init_bal = {}
        for col_group_key, value in init_bal_by_col_group.items():
            if isinstance(value, dict):
                # Lấy balance value cho method gốc
                simple_init_bal[col_group_key] = value.get('balance', 0.0)
            else:
                simple_init_bal[col_group_key] = value
        
        res = super(PartnerLedger, self)._get_report_line_move_line(options, aml_query_result, partner_line_id, simple_init_bal, level_shift)
        
        # Xử lý lũy tiến cho balance và foreign_balance
        for i, column in enumerate(options['columns']):
            col_expr_label = column['expression_label']
            if col_expr_label in ['balance', 'foreign_balance']:
                if col_expr_label == 'balance':
                    col_value = aml_query_result.get('balance', 0.0)
                else:  # foreign_balance
                    col_value = aml_query_result.get('foreign_balance', 0.0)
                
                if col_value is not None:
                    # Cộng dồn với initial balance
                    _logger.info(f"init_bal_by_col_group: {init_bal_by_col_group}")
                    init_balance = init_bal_by_col_group.get(column['column_group_key'], 0.0)
                    if isinstance(init_balance, dict):
                        init_balance = init_balance.get(col_expr_label, 0.0)
                    _logger.info(f"init_balance: {init_balance}")
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
        report = self.env.ref('account_reports.partner_ledger_report')
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

    def _query_partners(self, options):
        """ Executes the queries and performs all the computation.
        :return:        A list of tuple (partner, column_group_values) sorted by the table's model _order:
                        - partner is a res.parter record.
                        - column_group_values is a dict(column_group_key, fetched_values), where
                            - column_group_key is a string identifying a column group, like in options['column_groups']
                            - fetched_values is a dictionary containing:
                                - sum:                              {'debit': float, 'credit': float, 'balance': float, 'foreign_balance': float}
                                - (optional) initial_balance:       {'debit': float, 'credit': float, 'balance': float, 'foreign_balance': float}
                                - (optional) lines:                 [line_vals_1, line_vals_2, ...]
        """
        def assign_sum(row):
            fields_to_assign = ['balance', 'debit', 'credit', 'foreign_balance']
            if any(not company_currency.is_zero(row[field]) for field in fields_to_assign):
                groupby_partners.setdefault(row['groupby'], defaultdict(lambda: defaultdict(float)))
                for field in fields_to_assign:
                    groupby_partners[row['groupby']][row['column_group_key']][field] += row[field]

        company_currency = self.env.company.currency_id

        # Execute the queries and dispatch the results.
        query, params = self._get_query_sums(options)

        groupby_partners = {}

        self._cr.execute(query, params)
        for res in self._cr.dictfetchall():
            assign_sum(res)

        # Correct the sums per partner, for the lines without partner reconciled with a line having a partner
        query, params = self._get_sums_without_partner(options)

        self._cr.execute(query, params)
        totals = {}
        for total_field in ['debit', 'credit', 'balance', 'foreign_balance']:
            totals[total_field] = {col_group_key: 0 for col_group_key in options['column_groups']}

        for row in self._cr.dictfetchall():
            totals['debit'][row['column_group_key']] += row['debit']
            totals['credit'][row['column_group_key']] += row['credit']
            totals['balance'][row['column_group_key']] += row['balance']
            totals['foreign_balance'][row['column_group_key']] += row.get('foreign_balance', 0.0)

            if row['groupby'] not in groupby_partners:
                continue

            assign_sum(row)

        if None in groupby_partners:
            # Debit/credit are inverted for the unknown partner as the computation is made regarding the balance of the known partner
            for column_group_key in options['column_groups']:
                groupby_partners[None][column_group_key]['debit'] += totals['credit'][column_group_key]
                groupby_partners[None][column_group_key]['credit'] += totals['debit'][column_group_key]
                groupby_partners[None][column_group_key]['balance'] -= totals['balance'][column_group_key]
                groupby_partners[None][column_group_key]['foreign_balance'] -= totals['foreign_balance'][column_group_key]

        # Retrieve the partners to browse.
        # groupby_partners.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        if groupby_partners:
            # Note a search is done instead of a browse to preserve the table ordering.
            partners = self.env['res.partner'].with_context(active_test=False, prefetch_fields=False).search([('id', 'in', list(groupby_partners.keys()))])
        else:
            partners = []

        # Add 'Partner Unknown' if needed
        if None in groupby_partners.keys():
            partners = [p for p in partners] + [None]

        return [(partner, groupby_partners[partner.id if partner else None]) for partner in partners]

    def _report_expand_unfoldable_line_partner_ledger(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        def init_load_more_progress(line_dict):
            progress = {}
            for column, line_col in zip(options['columns'], line_dict['columns']):
                if column['expression_label'] in ['balance', 'foreign_balance']:
                    col_group_key = column['column_group_key']
                    if col_group_key not in progress:
                        progress[col_group_key] = {}
                    progress[col_group_key][column['expression_label']] = line_col.get('no_format', 0)
            return progress

        report = self.env.ref('account_reports.partner_ledger_report')
        markup, model, record_id = report._parse_line_id(line_dict_id)[-1]

        if model != 'res.partner':
            raise UserError(_("Wrong ID for partner ledger line to expand: %s", line_dict_id))

        prefix_groups_count = 0
        for markup, dummy1, dummy2 in report._parse_line_id(line_dict_id):
            if markup.startswith('groupby_prefix_group:'):
                prefix_groups_count += 1
        level_shift = prefix_groups_count * 2

        lines = []

        # Get initial balance
        if offset == 0:
            if unfold_all_batch_data:
                init_balance_by_col_group = unfold_all_batch_data['initial_balances'][record_id]
            else:
                init_balance_by_col_group = self._get_initial_balance_values([record_id], options)[record_id]
            initial_balance_line = report._get_partner_and_general_ledger_initial_balance_line(options, line_dict_id, init_balance_by_col_group, level_shift=level_shift)
            if initial_balance_line:
                lines.append(initial_balance_line)

                # For the first expansion of the line, the initial balance line gives the progress
                progress = init_load_more_progress(initial_balance_line)

        limit_to_load = report.load_more_limit + 1 if report.load_more_limit and not self._context.get('print_mode') else None

        if unfold_all_batch_data:
            aml_results = unfold_all_batch_data['aml_values'][record_id]
        else:
            aml_results = self._get_aml_values(options, [record_id], offset=offset, limit=limit_to_load)[record_id]

        has_more = False
        treated_results_count = 0
        next_progress = progress
        for result in aml_results:
            if not self._context.get('print_mode') and report.load_more_limit and treated_results_count == report.load_more_limit:
                # We loaded one more than the limit on purpose: this way we know we need a "load more" line
                has_more = True
                break

            new_line = self._get_report_line_move_line(options, result, line_dict_id, next_progress, level_shift=level_shift)
            lines.append(new_line)
            next_progress = init_load_more_progress(new_line)
            treated_results_count += 1

        return {
            'lines': lines,
            'offset_increment': treated_results_count,
            'has_more': has_more,
            'progress': json.dumps(next_progress)
        }

    def _get_query_sums(self, options):
        # Lấy thông tin currency từ options
        currency_env = self.env['res.currency']
        company_currency = self.env.company.currency_id
        currency, currency_nt = self._get_selected_currency(options, company_currency, currency_env)
            
        params = []
        queries = []
        report = self.env.ref('account_reports.partner_ledger_report')
        
        # Create the currency table.
        ct_query = self.env['res.currency']._get_query_currency_table(options)
            
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            tables, where_clause, where_params = report._query_get(column_group_options, 'normal')
            params.append(column_group_key)
            # Parameters for SQL function calls: 1 + (3×4) = 13 total parameters
            params += [*where_params]
            
            # Tính foreign_balance dựa trên currency_nt
            # Nếu aml.currency_id = company.currency_id thì foreign_balance = 0
            if currency_nt != company_currency:
                foreign_balance_expr = f'SUM(CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.amount_currency END)'
            else:
                foreign_balance_expr = f'SUM(CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.balance END)'
            
            queries.append(f"""
                SELECT
                    account_move_line.partner_id AS groupby,
                    %s AS column_group_key,
                    SUM(CASE WHEN account_move_line.debit = 0 THEN 0 ELSE {'account_move_line.debit' if currency == company_currency else 'abs(account_move_line.amount_currency)'} END) AS debit,
                    SUM(CASE WHEN account_move_line.credit = 0 THEN 0 ELSE {'account_move_line.credit' if currency == company_currency else 'abs(account_move_line.amount_currency)'} END) AS credit,
                    SUM({'account_move_line.balance' if currency == company_currency else 'abs(account_move_line.amount_currency)'}) AS balance,
                    {foreign_balance_expr} AS foreign_balance
                FROM {tables}
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                GROUP BY account_move_line.partner_id
            """)

        return ' UNION ALL '.join(queries), params

    def _get_sums_without_partner(self, options):
        """ Get the sums for the move lines not linked to a partner, but reconciled with a partner.
        """
        # Lấy thông tin currency từ options
        currency_env = self.env['res.currency']
        company_currency = self.env.company.currency_id
        currency, currency_nt = self._get_selected_currency(options, company_currency, currency_env)
        
        params = []
        queries = []
        report = self.env.ref('account_reports.partner_ledger_report')
        
        # Create the currency table.
        ct_query = self.env['res.currency']._get_query_currency_table(options)
        
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            tables, where_clause, where_params = report._query_get(column_group_options, 'normal')
            params.append(column_group_key)
            params += [*where_params]
            
            # Tính foreign_balance dựa trên currency_nt
            # Nếu aml.currency_id = company.currency_id thì foreign_balance = 0
            if currency_nt != company_currency:
                foreign_balance_expr = f'SUM(CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.amount_currency END)'
            else:
                foreign_balance_expr = f'SUM(CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.balance END)'
            
            queries.append(f"""
                SELECT
                    account_move_line.partner_id AS groupby,
                    %s AS column_group_key,
                    SUM(CASE WHEN account_move_line.debit = 0 THEN 0 ELSE {'account_move_line.debit' if currency == company_currency else 'abs(account_move_line.amount_currency)'} END) AS debit,
                    SUM(CASE WHEN account_move_line.credit = 0 THEN 0 ELSE {'account_move_line.credit' if currency == company_currency else 'abs(account_move_line.amount_currency)'} END) AS credit,
                    SUM({'account_move_line.balance' if currency == company_currency else 'abs(account_move_line.amount_currency)'}) AS balance,
                    {foreign_balance_expr} AS foreign_balance
                FROM {tables}
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause} AND account_move_line.partner_id IS NULL
                GROUP BY account_move_line.partner_id
            """)

        return ' UNION ALL '.join(queries), params

    def _get_initial_balance_values(self, partner_ids, options):
        # Lấy thông tin currency từ options
        currency_env = self.env['res.currency']
        company_currency = self.env.company.currency_id
        currency, currency_nt = self._get_selected_currency(options, company_currency, currency_env)

        queries = []
        params = []
        report = self.env.ref('account_reports.partner_ledger_report')
        ct_query = self.env['res.currency']._get_query_currency_table(options)
        
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            # Create opening balance options - sử dụng dữ liệu đã cập nhật
            new_options = self._get_options_initial_balance(column_group_options)
            tables, where_clause, where_params = report._query_get(new_options, 'normal', domain=[('partner_id', 'in', partner_ids)])
            params.append(column_group_key)
            # Parameters for SQL function calls: 1 + (3×4) = 13 total parameters
            params += [*where_params]
            
            # Tính foreign_balance dựa trên currency_nt - sử dụng dữ liệu đã cập nhật
            # Nếu aml.currency_id = company.currency_id thì foreign_balance = 0
            if currency_nt != company_currency:
                foreign_balance_expr = f'SUM(CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.amount_currency END)'
            else:
                foreign_balance_expr = f'SUM(CASE WHEN account_move_line.currency_id = {company_currency.id} THEN 0 ELSE account_move_line.balance END)'
            
            queries.append(f"""
                SELECT
                    account_move_line.partner_id,
                    %s AS column_group_key,
                    SUM(CASE WHEN account_move_line.debit = 0 THEN 0 ELSE {'account_move_line.debit' if currency == company_currency else 'abs(account_move_line.amount_currency)'} END) AS debit,
                    SUM(CASE WHEN account_move_line.credit = 0 THEN 0 ELSE {'account_move_line.credit' if currency == company_currency else 'abs(account_move_line.amount_currency)'} END) AS credit,
                    SUM({'account_move_line.balance' if currency == company_currency else 'abs(account_move_line.amount_currency)'}) AS balance,
                    {foreign_balance_expr} AS foreign_balance
                FROM {tables}
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                GROUP BY account_move_line.partner_id
            """)

        self._cr.execute(" UNION ALL ".join(queries), params)

        init_balance_by_col_group = {
            partner_id: {column_group_key: {} for column_group_key in options['column_groups']}
            for partner_id in partner_ids
        }
        for result in self._cr.dictfetchall():
            # Tính balance từ debit - credit thay vì dùng trực tiếp từ query
            result['balance'] = result.get('debit', 0.0) - result.get('credit', 0.0)
            # Đảm bảo foreign_balance có giá trị và đúng loại tiền tệ
            if 'foreign_balance' not in result or result.get('foreign_balance') is None:
                # Sử dụng balance nếu không có foreign_balance
                result['foreign_balance'] = result.get('balance', 0.0)
            init_balance_by_col_group[result['partner_id']][result['column_group_key']] = result
        return init_balance_by_col_group

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
