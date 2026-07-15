# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_line_ids = fields.One2many(
        'account.move.line',
        'move_id',
        string='Invoice lines',
        copy=False,
        readonly=True,
        domain=[('display_type', 'in', ('product', 'line_section', 'line_note')),('hide_in_detail_invoice','=',False)],
        states={'draft': [('readonly', False)]},
    )

    invoice_line_taxs_ids = fields.One2many(
        'account.move.line',
        'move_id',
        string='Invoice lines Tax',
        copy=False,
        readonly=True,
        domain=[('account_id.tax_account_collection_payment','=',True)],
        states={'draft': [('readonly', False)]},
    )

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    create_in_detail_move = fields.Boolean(copy=False)
    hide_in_detail_invoice = fields.Boolean(compute="_compute_hide_in_detail_invoice",search="_search_hide_in_detail_invoice")
    tax_amount_value = fields.Monetary('Tax value',compute="_compute_tax_amount_value",store=True)

    @api.depends('price_subtotal','tax_ids')
    def _compute_tax_amount_value(self):
        for line in self:
            tax_amount_value = False
            price_unit = line.price_unit * (1 - (line.discount / 100.0))
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                )
                tax_amount_value = taxes_res['total_included'] - taxes_res['total_excluded']
            line.tax_amount_value = tax_amount_value

    def _compute_hide_in_detail_invoice(self):
        for res in self:
            res.hide_in_detail_invoice = True if res.create_in_detail_move and res.account_id.tax_account_collection_payment else False

    def _search_hide_in_detail_invoice(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))

        movelines = self.search([('create_in_detail_move','=',True),('account_id.tax_account_collection_payment','=',True)])

        if operator == '!=':
            value = not value

        return [('id', 'in' if value else 'not in', movelines.ids)]

