 # -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from functools import lru_cache
   
class AccountReport(models.Model):
    _inherit = 'account.report'

    def _filter_out_folded_children(self, lines):
        if self.name == _('Partner Ledger'):
            rslt = []
            folded_lines = set()
            for line in lines:
                if line.get('unfoldable') and line.get('unfolded'):
                    folded_lines.add(line['id'])

                if 'parent_id' not in line or line['parent_id'] not in folded_lines:
                    rslt.append(line)
            return rslt
        else:
            return super(AccountReport,self)._filter_out_folded_children(lines)