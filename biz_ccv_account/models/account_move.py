# -*- coding: utf-8 -*-

from odoo import api, fields, models,_
from odoo.tools import frozendict

class AccountMove(models.Model):
    _inherit = 'account.move'

    # def _update_account_product(self):
    #     for res in self:
    #         product_lines = res.line_ids.filtered(lambda line: line.display_type == 'product' and line.move_id.is_invoice(True))
    #         for line in product_lines:
    #             if line.product_id:
    #                 fiscal_position = line.move_id.fiscal_position_id
    #                 accounts = line.with_company(line.company_id).product_id\
    #                     .product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
    #                 if line.move_id.is_sale_document(include_receipts=True):
    #                     line.account_id = accounts['income'] or line.account_id
    #                 elif line.move_id.is_purchase_document(include_receipts=True):
    #                     line.account_id = accounts['expense'] or line.account_id
    #             elif line.partner_id:
    #                 line.account_id = self.env['account.account']._get_most_frequent_account_for_partner(
    #                     company_id=line.company_id.id,
    #                     partner_id=line.partner_id.id,
    #                     move_type=line.move_id.move_type,
    #                 )

    def recompute_name(self):
        self = self.with_context(skip_invoice_sync=True)
        self.write({
            'name': '/',
        })
        self._compute_name()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_all_tax(self):
        super(AccountMoveLine, self)._compute_all_tax()
        for line in self:
            for key in list(line.compute_all_tax.keys()):
                new_key = dict(key)
                if 'partner_id' in new_key:
                    new_key.update({
                        'partner_id': line.partner_id.id or line.move_id.partner_id.id
                    })
                    new_key = frozendict(new_key)
                    line.compute_all_tax[new_key] = line.compute_all_tax.pop(key)