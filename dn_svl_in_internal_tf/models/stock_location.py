# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockLocation(models.Model):
    """Extend stock.location with a per-location valuation account.

    Account resolution order (see _get_valuation_account):
      1. Account set on the location itself (dn_valuation_account_id).
      2. Recursive lookup up the parent location tree.
      3. Fallback to product.category.property_stock_valuation_account_id.
    """

    _inherit = 'stock.location'

    dn_valuation_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Valuation Account (DN)',
        company_dependent=True,
        ondelete='restrict',
        check_company=True,
        domain=[
            ('account_type', 'not in', (
                'asset_receivable',
                'liability_payable',
                'asset_cash',
                'liability_credit_card',
            ))
        ],
        help=(
            'Accounting account representing the stock value held at this '
            'location. If left empty, the system will look up the parent '
            'location hierarchy and finally fall back to the product category.'
        ),
    )

    def _get_valuation_account(self, product=None):
        """Return the effective valuation account for this location.

        Resolution order:
          1. ``dn_valuation_account_id`` on this location.
          2. ``dn_valuation_account_id`` on each ancestor location (recursive).
          3. ``product.categ_id.property_stock_valuation_account_id``
             when ``product`` is provided.

        :param product: ``product.product`` or ``product.template`` record
                        used as the last-resort fallback. May be ``None``.
        :returns: ``account.account`` record, or an empty recordset.
        """
        self.ensure_one()
        location = self
        while location:
            if location.dn_valuation_account_id:
                return location.dn_valuation_account_id
            location = location.location_id or False

        # Fallback: account from the product category
        if product:
            categ = product.categ_id if hasattr(product, 'categ_id') else None
            if categ:
                acc = categ.property_stock_valuation_account_id
                if not acc:
                    # Company-dependent fallback pattern for Odoo 19
                    acc = categ._fields[
                        'property_stock_valuation_account_id'
                    ].get_company_dependent_fallback(categ)
                if acc:
                    return acc

        return self.env['account.account']
