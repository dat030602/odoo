# -*- coding: utf-8 -*-

from odoo import models

class TrialBalanceCustomHandler(models.AbstractModel):
    _inherit = 'account.trial.balance.report.handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        lines = super()._dynamic_lines_generator(report, options, all_column_groups_expression_totals)
        
        filtered_lines = []
        for dummy, line in lines:
            # We only want to filter out account lines that have exactly 0 everywhere.
            # Other lines (like the Total line) should be kept.
            try:
                res_model = report._get_model_info_from_id(line['id'])[0]
            except Exception:
                res_model = None

            if res_model == 'account.account':
                all_zero = True
                for col in line.get('columns', []):
                    val = col.get('no_format', 0.0)
                    if isinstance(val, (int, float)) and abs(val) > 0.001:
                        all_zero = False
                        break
                
                if all_zero:
                    continue
            
            filtered_lines.append((0, line))
            
        return filtered_lines
