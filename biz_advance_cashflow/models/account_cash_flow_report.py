# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.misc import get_lang


class CashFlowReportCustomHandler(models.AbstractModel):
    _inherit = 'account.cash.flow.report.handler'

    def _get_report_data(self, report, options, layout_data):
        report_data = super(CashFlowReportCustomHandler, self)._get_report_data(report, options, layout_data)
        currency_table_query = self.env['res.currency']._get_query_currency_table(options)
        payment_move_ids, payment_account_ids = self._get_liquidity_move_ids(report, options)
        tags_ids = self._get_tags_ids()
        cashflow_tag_ids = self._get_cashflow_tag_ids()

        if options.get("analytic_accounts_groupby"):
            for account_group_by in options.get("analytic_accounts_groupby"):
                for aml_groupby_account in self._custom_get_liquidity_moves(report, options, currency_table_query, payment_account_ids, payment_move_ids, cashflow_tag_ids, account_group_by):
                    for aml_data in aml_groupby_account.values():
                        self._dispatch_aml_data(tags_ids, aml_data, layout_data, report_data)

        if options.get("analytic_accounts_groupby"):
            for account_group_by in options.get("analytic_accounts_groupby"):
                for aml_groupby_account in self._custom_get_reconciled_moves(report, options, currency_table_query, payment_account_ids, payment_move_ids, cashflow_tag_ids, account_group_by):
                    for aml_data in aml_groupby_account.values():
                        # print(aml_data["account_name"], ":", aml_data["balance"])
                        self._dispatch_aml_data(tags_ids, aml_data, layout_data, report_data)

        return report_data

    def _get_custom_move_ids_query(self, report, payment_account_ids, column_group_options, account_group_by=None):
        ''' Get all liquidity moves to be part of the cash flow statement.
        :param payment_account_ids: A tuple containing all account.account's ids being used in a liquidity journal.
        :return: query: The SQL query to retrieve the move IDs.
        '''
        custom_payment_account_ids = list(payment_account_ids)
        tables, where_clause, where_params = report._custom_query_get(column_group_options, 'strict_range', [('account_id', 'in', custom_payment_account_ids)], account_group_by)
        if account_group_by:
            where_clause += """ AND "account_move_line"."analytic_distribution" -> '%s' is not null """ % account_group_by
        query = f'''
            SELECT
                array_agg(DISTINCT account_move_line.move_id) AS move_id
            FROM {tables}
            WHERE {where_clause}
        '''
        return self.env.cr.mogrify(query, where_params).decode(self.env.cr.connection.encoding)

    def _custom_get_liquidity_moves(self, report, options, currency_table_query, payment_account_ids, payment_move_ids, cash_flow_tag_ids, account_group_by):
        ''' Fetch all information needed to compute lines from liquidity moves.
        The difficulty is to represent only the not-reconciled part of balance.

        :param options:                 The report options.
        :param currency_table_query:    The floating query to handle a multi-company/multi-currency environment.
        :param payment_move_ids:        A tuple containing all account.move's ids being the liquidity moves.
        :param payment_account_ids:     A tuple containing all account.account's ids being used in a liquidity journal.
        :return:                        A list of tuple (account_id, account_code, account_name, account_type, amount).
        '''
        if not payment_move_ids:
            return []

        reconciled_aml_groupby_account = {}

        queries = []
        params = []
        if self.pool['account.account'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            account_name = f"COALESCE(account_account.name->>'{lang}', account_account.name->>'en_US')"
        else:
            account_name = 'account_account.name'
        custom_column_group_key = False
        for group_key in options['column_groups']:
            group_options = self.env["account.report"]._get_column_group_options(options, group_key)
            if group_options.get("analytic_accounts_list") and group_options.get("analytic_accounts_list")[0] == account_group_by:
                custom_column_group_key = group_key

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            if column_group_options and not 'analytic_accounts_list' in column_group_options:
                continue
            if column_group_key != custom_column_group_key:
                continue
            move_ids = self._get_custom_move_ids_query(report, payment_account_ids, column_group_options, account_group_by)
            queries.append(f'''
                (WITH payment_move_ids AS ({move_ids})
                -- Credit amount of each account
                SELECT
                    %s AS column_group_key,
                    account_move_line.account_id,
                    account_account.code AS account_code,
                    {account_name} AS account_name,
                    account_account.account_type AS account_account_type,
                    account_account_account_tag.account_account_tag_id AS account_tag_id,
                    SUM(ROUND(account_partial_reconcile.amount * currency_table.rate, currency_table.precision)) * CAST(account_move_line.analytic_distribution::json->>'{account_group_by}' AS DECIMAL) / 100 AS balance
                FROM account_move_line
                LEFT JOIN {currency_table_query}
                    ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN account_partial_reconcile
                    ON account_partial_reconcile.credit_move_id = account_move_line.id
                JOIN account_account
                    ON account_account.id = account_move_line.account_id
                LEFT JOIN account_account_account_tag
                    ON account_account_account_tag.account_account_id = account_move_line.account_id
                    AND account_account_account_tag.account_account_tag_id IN %s
                WHERE account_move_line.move_id IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND account_move_line.account_id NOT IN %s
                    AND account_partial_reconcile.max_date BETWEEN %s AND %s
                GROUP BY account_move_line.company_id, account_move_line.account_id, account_account.code, account_name, account_account.account_type, account_account_account_tag.account_account_tag_id, account_move_line.analytic_distribution

                UNION ALL

                -- Debit amount of each account
                SELECT
                    %s AS column_group_key,
                    account_move_line.account_id,
                    account_account.code AS account_code,
                    {account_name} AS account_name,
                    account_account.account_type AS account_account_type,
                    account_account_account_tag.account_account_tag_id AS account_tag_id,
                    -SUM(ROUND(account_partial_reconcile.amount * currency_table.rate, currency_table.precision)) * CAST(account_move_line.analytic_distribution::json->>'{account_group_by}' AS DECIMAL) / 100 AS balance
                FROM account_move_line
                LEFT JOIN {currency_table_query}
                    ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN account_partial_reconcile
                    ON account_partial_reconcile.debit_move_id = account_move_line.id
                JOIN account_account
                    ON account_account.id = account_move_line.account_id
                LEFT JOIN account_account_account_tag
                    ON account_account_account_tag.account_account_id = account_move_line.account_id
                    AND account_account_account_tag.account_account_tag_id IN %s
                WHERE account_move_line.move_id IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND account_move_line.account_id NOT IN %s
                    AND account_partial_reconcile.max_date BETWEEN %s AND %s
                GROUP BY account_move_line.company_id, account_move_line.account_id, account_account.code, account_name, account_account.account_type, account_account_account_tag.account_account_tag_id, account_move_line.analytic_distribution

                UNION ALL

                -- Total amount of each account
                SELECT
                    %s AS column_group_key,
                    account_move_line.account_id AS account_id,
                    account_account.code AS account_code,
                    {account_name} AS account_name,
                    account_account.account_type AS account_account_type,
                    account_account_account_tag.account_account_tag_id AS account_tag_id,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) * CAST(account_move_line.analytic_distribution::json->>'{account_group_by}' AS DECIMAL) / 100 AS balance
                FROM account_move_line
                LEFT JOIN {currency_table_query}
                    ON currency_table.company_id = account_move_line.company_id
                JOIN account_account
                    ON account_account.id = account_move_line.account_id
                LEFT JOIN account_account_account_tag
                    ON account_account_account_tag.account_account_id = account_move_line.account_id
                    AND account_account_account_tag.account_account_tag_id IN %s
                WHERE account_move_line.move_id IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND account_move_line.account_id NOT IN %s
                GROUP BY account_move_line.account_id, account_account.code, account_name, account_account.account_type, account_account_account_tag.account_account_tag_id, account_move_line.analytic_distribution)
            ''')

            date_from = column_group_options['date']['date_from']
            date_to = column_group_options['date']['date_to']

            params += [
                custom_column_group_key, tuple(cash_flow_tag_ids), payment_account_ids, date_from, date_to,
                custom_column_group_key, tuple(cash_flow_tag_ids), payment_account_ids, date_from, date_to,
                custom_column_group_key, tuple(cash_flow_tag_ids), payment_account_ids,
            ]
        self._cr.execute(' UNION ALL '.join(queries), params)

        for aml_data in self._cr.dictfetchall():
            # print("_custom_get_liquidity_moves")
            # print("aml_data", aml_data.get("account_id"), aml_data.get("balance"), aml_data.get("column_group_key"))
            reconciled_aml_groupby_account.setdefault(aml_data['account_id'], {})
            reconciled_aml_groupby_account[aml_data['account_id']].setdefault(aml_data['column_group_key'], {
                'column_group_key': aml_data['column_group_key'],
                'account_id': aml_data['account_id'],
                'account_code': aml_data['account_code'],
                'account_name': aml_data['account_name'],
                'account_account_type': aml_data['account_account_type'],
                'account_tag_id': aml_data['account_tag_id'],
                'balance': 0.0,
            })
            if aml_data['balance'] is not None:
                reconciled_aml_groupby_account[aml_data['account_id']][aml_data['column_group_key']]['balance'] -= aml_data['balance']

        return list(reconciled_aml_groupby_account.values())

    def _custom_get_reconciled_moves(self, report, options, currency_table_query, payment_account_ids, payment_move_ids, cash_flow_tag_ids, account_group_by):
        if not payment_move_ids:
            return []

        reconciled_account_ids = {column_group_key: set() for column_group_key in options['column_groups']}
        reconciled_percentage_per_move = {column_group_key: {} for column_group_key in options['column_groups']}

        queries = []
        params = []

        custom_column_group_key = False
        for group_key in options['column_groups']:
            group_options = self.env["account.report"]._get_column_group_options(options, group_key)
            if group_options.get("analytic_accounts_list") and group_options.get("analytic_accounts_list")[0] == account_group_by:
                custom_column_group_key = group_key
                break

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            if column_group_options and not 'analytic_accounts_list' in column_group_options:
                continue
            if column_group_key != custom_column_group_key:
                continue
            move_ids = self._get_custom_move_ids_query(report, payment_account_ids, column_group_options, account_group_by)

            queries.append(f'''
                (WITH payment_move_ids AS ({move_ids})
                SELECT
                    %s AS column_group_key,
                    debit_line.move_id,
                    debit_line.account_id,
                    SUM(account_partial_reconcile.amount) * CAST(credit_line.analytic_distribution::json->>'{account_group_by}' AS DECIMAL) / 100 AS balance
                FROM account_move_line AS credit_line
                LEFT JOIN account_partial_reconcile
                    ON account_partial_reconcile.credit_move_id = credit_line.id
                INNER JOIN account_move_line AS debit_line
                    ON debit_line.id = account_partial_reconcile.debit_move_id
                WHERE credit_line.move_id IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND credit_line.account_id NOT IN %s
                    AND credit_line.credit > 0.0
                    AND debit_line.move_id NOT IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND account_partial_reconcile.max_date BETWEEN %s AND %s
                GROUP BY debit_line.move_id, debit_line.account_id, credit_line.analytic_distribution

                UNION ALL

                SELECT
                    %s AS column_group_key,
                    credit_line.move_id,
                    credit_line.account_id,
                    -SUM(account_partial_reconcile.amount) * CAST(debit_line.analytic_distribution::json->>'{account_group_by}' AS DECIMAL) / 100 AS balance
                FROM account_move_line AS debit_line
                LEFT JOIN account_partial_reconcile
                    ON account_partial_reconcile.debit_move_id = debit_line.id
                INNER JOIN account_move_line AS credit_line
                    ON credit_line.id = account_partial_reconcile.credit_move_id
                WHERE debit_line.move_id IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND debit_line.account_id NOT IN %s
                    AND debit_line.debit > 0.0
                    AND credit_line.move_id NOT IN (SELECT unnest(payment_move_ids.move_id) FROM payment_move_ids)
                    AND account_partial_reconcile.max_date BETWEEN %s AND %s
                GROUP BY credit_line.move_id, credit_line.account_id, debit_line.analytic_distribution)
            ''')

            params += [
                custom_column_group_key,
                payment_account_ids,
                column_group_options['date']['date_from'],
                column_group_options['date']['date_to'],
            ] * 2

        self._cr.execute(' UNION ALL '.join(queries), params)

        for aml_data in self._cr.dictfetchall():
            # print("For Case 1", aml_data["balance"])
            reconciled_percentage_per_move[aml_data['column_group_key']].setdefault(aml_data['move_id'], {})
            reconciled_percentage_per_move[aml_data['column_group_key']][aml_data['move_id']].setdefault(aml_data['account_id'], [0.0, 0.0])
            if aml_data["balance"] is None:
                aml_data["balance"] = 0.0
            reconciled_percentage_per_move[aml_data['column_group_key']][aml_data['move_id']][aml_data['account_id']][0] += aml_data['balance']

            reconciled_account_ids[aml_data['column_group_key']].add(aml_data['account_id'])

        if not reconciled_percentage_per_move:
            return []

        queries = []
        params = []

        for column in options['columns']:
            if column and column.get("column_group_key") != custom_column_group_key:
                continue
            queries.append(f'''
                SELECT
                    %s AS column_group_key,
                    account_move_line.move_id,
                    account_move_line.account_id,
                    SUM(account_move_line.balance) AS balance
                FROM account_move_line
                JOIN {currency_table_query}
                    ON currency_table.company_id = account_move_line.company_id
                WHERE account_move_line.move_id IN %s
                    AND account_move_line.account_id IN %s
                    AND account_move_line.analytic_distribution -> '{account_group_by}' is not null
                GROUP BY account_move_line.move_id, account_move_line.account_id, account_move_line.analytic_distribution
            ''')

            params += [column['column_group_key'], tuple(reconciled_percentage_per_move[column['column_group_key']].keys()) or (None,), tuple(reconciled_account_ids[column['column_group_key']]) or (None,)]

        self._cr.execute(' UNION ALL '.join(queries), params)

        for aml_data in self._cr.dictfetchall():
            # print("For Case 2", aml_data["balance"])
            if aml_data['account_id'] in reconciled_percentage_per_move[aml_data['column_group_key']][aml_data['move_id']]:
                reconciled_percentage_per_move[aml_data['column_group_key']][aml_data['move_id']][aml_data['account_id']][1] += aml_data['balance']

        reconciled_aml_per_account = {}

        queries = []
        params = []
        if self.pool['account.account'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            account_name = f"COALESCE(account_account.name->>'{lang}', account_account.name->>'en_US')"
        else:
            account_name = 'account_account.name'

        for column in options['columns']:
            if column and column.get("column_group_key") != custom_column_group_key:
                continue
            queries.append(f'''
                SELECT
                    %s AS column_group_key,
                    account_move_line.move_id,
                    account_move_line.account_id,
                    account_account.code AS account_code,
                    {account_name} AS account_name,
                    account_account.account_type AS account_account_type,
                    account_account_account_tag.account_account_tag_id AS account_tag_id,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) * CAST(account_move_line.analytic_distribution::json->>'{account_group_by}' AS DECIMAL) / 100 AS balance
                FROM account_move_line
                LEFT JOIN {currency_table_query}
                    ON currency_table.company_id = account_move_line.company_id
                JOIN account_account
                    ON account_account.id = account_move_line.account_id
                LEFT JOIN account_account_account_tag
                    ON account_account_account_tag.account_account_id = account_move_line.account_id
                    AND account_account_account_tag.account_account_tag_id IN %s
                WHERE account_move_line.move_id IN %s AND account_move_line.analytic_distribution -> '{account_group_by}' is not null
                GROUP BY account_move_line.move_id, account_move_line.account_id, account_account.code, account_name, account_account.account_type, account_account_account_tag.account_account_tag_id, account_move_line.analytic_distribution
            ''')

            params += [column['column_group_key'], tuple(cash_flow_tag_ids), tuple(reconciled_percentage_per_move[column['column_group_key']].keys()) or (None,)]

        self._cr.execute(' UNION ALL '.join(queries), params)

        for aml_data in self._cr.dictfetchall():
            aml_column_group_key = aml_data['column_group_key']
            aml_move_id = aml_data['move_id']
            aml_account_id = aml_data['account_id']
            aml_account_code = aml_data['account_code']
            aml_account_name = aml_data['account_name']
            aml_account_account_type = aml_data['account_account_type']
            aml_account_tag_id = aml_data['account_tag_id']
            aml_balance = aml_data['balance']

            # if aml_account_name == "Doanh thu bán hàng hóa nhập khẩu":
            #     print("===BASE aml_balance", aml_balance)

            # # Compute the total reconciled for the whole move.
            # total_reconciled_amount = 0.0
            # total_amount = 0.0
            #
            # for reconciled_amount, amount in reconciled_percentage_per_move[aml_column_group_key][aml_move_id].values():
            #     total_reconciled_amount += reconciled_amount
            #     total_amount += amount
            #
            # # Compute matched percentage for each account.
            # if total_amount and aml_account_id not in reconciled_percentage_per_move[aml_column_group_key][aml_move_id]:
            #     # Lines being on reconciled moves but not reconciled with any liquidity move must be valued at the
            #     # percentage of what is actually paid.
            #     reconciled_percentage = total_reconciled_amount / total_amount
            #     aml_balance *= reconciled_percentage
            # elif not total_amount and aml_account_id in reconciled_percentage_per_move[aml_column_group_key][aml_move_id]:
            #     # The total amount to reconcile is 0. In that case, only add entries being on these accounts. Otherwise,
            #     # this special case will lead to an unexplained difference equivalent to the reconciled amount on this
            #     # account.
            #     # E.g:
            #     #
            #     # Liquidity move:
            #     # Account         | Debit     | Credit
            #     # --------------------------------------
            #     # Bank            |           | 100
            #     # Receivable      | 100       |
            #     #
            #     # Reconciled move:                          <- reconciled_amount=100, total_amount=0.0
            #     # Account         | Debit     | Credit
            #     # --------------------------------------
            #     # Receivable      |           | 200
            #     # Receivable      | 200       |             <- Only the reconciled part of this entry must be added.
            #     aml_balance = -reconciled_percentage_per_move[aml_column_group_key][aml_move_id][aml_account_id][0]
            # else:
            #     # Others lines are not considered.
            #     continue

            reconciled_aml_per_account.setdefault(aml_account_id, {})
            reconciled_aml_per_account[aml_account_id].setdefault(aml_column_group_key, {
                'column_group_key': aml_column_group_key,
                'account_id': aml_account_id,
                'account_code': aml_account_code,
                'account_name': aml_account_name,
                'account_account_type': aml_account_account_type,
                'account_tag_id': aml_account_tag_id,
                'balance': 0.0,
            })
            reconciled_aml_per_account[aml_account_id][aml_column_group_key]['balance'] -= aml_balance
            # if reconciled_aml_per_account[aml_account_id][aml_column_group_key]['account_name'] == "Doanh thu bán hàng hóa nhập khẩu":
            #     print("===CHILD", account_group_by,  reconciled_aml_per_account[aml_account_id][aml_column_group_key]['account_name'], ":", reconciled_aml_per_account[aml_account_id][aml_column_group_key]['balance'])

        return list(reconciled_aml_per_account.values())