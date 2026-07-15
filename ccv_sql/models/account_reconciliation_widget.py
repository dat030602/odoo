# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.osv import expression

class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    @api.model
    def _domain_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, search_str=''):
        date_from = False
        date_to = False
        
        if search_str and '|||' in search_str:
            parts = search_str.split('|||')
            search_str = parts[0]
            if len(parts) > 1 and parts[1]:
                date_from = parts[1]
            if len(parts) > 2 and parts[2]:
                date_to = parts[2]
                
        domain = super()._domain_move_lines_for_manual_reconciliation(account_id, partner_id, excluded_ids, search_str)
        
        if date_from:
            domain = expression.AND([domain, [('date', '>=', date_from)]])
        if date_to:
            domain = expression.AND([domain, [('date', '<=', date_to)]])
            
        return domain
