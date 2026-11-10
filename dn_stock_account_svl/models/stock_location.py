# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class StockLocation(models.Model):
    """Extend stock.location with a per-location valuation account.

    Account resolution order (see _get_valuation_account):
      - When product is provided:
        * If product.use_location_valuation_account is True:
          Location account (with parent hierarchy fallback) -> Category account fallback.
        * If product.use_location_valuation_account is False (default):
          Category account -> Location account (with parent hierarchy fallback).
        * If neither is found, raises UserError.
      - When product is None:
        * Location account (with parent hierarchy fallback).
        * If not found, raises UserError.
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

        :param product: product.product or product.template record or None.
        :returns: account.account record.
        :raises UserError: If no valuation account can be found.
        """
        self.ensure_one()
        if product:
            use_location_first = bool(getattr(product, 'use_location_valuation_account', False))
            loc_account = self._get_location_valuation_account()
            cat_account = self._get_category_valuation_account(product)

            if use_location_first:
                resolved = loc_account or cat_account
            else:
                resolved = cat_account or loc_account

            if not resolved:
                raise UserError(_(
                    "Stock Valuation Account is not configured for product '%(product)s' on either its category or location '%(location)s'.",
                    product=product.display_name,
                    location=self.complete_name or self.name,
                ))
            return resolved

        # product is None
        loc_account = self._get_location_valuation_account()
        if not loc_account:
            raise UserError(_(
                "Stock Valuation Account is not configured for location '%(location)s'.",
                location=self.complete_name or self.name,
            ))
        return loc_account

    def _get_location_valuation_account(self):
        """Find valuation account configured directly on this location or its ancestors."""
        loc = self
        while loc:
            if loc.dn_valuation_account_id:
                return loc.dn_valuation_account_id
            loc = loc.location_id or False
        return self.env['account.account']

    def _get_category_valuation_account(self, product):
        """Find valuation account configured on the product category."""
        return product.categ_id.property_stock_valuation_account_id or self.env['account.account']
