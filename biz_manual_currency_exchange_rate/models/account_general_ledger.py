# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from odoo import models, fields
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)

class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _get_aml_line(self, report, parent_line_id, options, eval_dict, init_bal_by_col_group):
        res = super(GeneralLedgerCustomHandler, self)._get_aml_line(report, parent_line_id, options, eval_dict, init_bal_by_col_group)
        columns = res['columns']
        index_update = []
        
        key = list(eval_dict.keys())[0]
        move_line_id = eval_dict[key]['id']
        move_line = self.env['account.move.line'].browse(move_line_id)

        for count, column_option in enumerate(options['columns']):
            if column_option.get("expression_label") == 'currency_rate':
                index_update.append(count)

        for column_index, column in enumerate(columns):
            if column_index in index_update:
                formatted_value = report.format_value(move_line.move_id.inverse_manural_currency_exchange_rate, figure_type='integer')
                columns[column_index] = {
                    'name': formatted_value,
                    'no_format': move_line.move_id.inverse_manural_currency_exchange_rate,
                    'class': 'number'
                    }

        return res
    