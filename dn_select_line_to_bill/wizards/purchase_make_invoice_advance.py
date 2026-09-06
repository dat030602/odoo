# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import formatLang

class PurchaseAdvancePaymentInv(models.TransientModel):
    _name = 'purchase.advance.payment.inv'
    _description = "Purchase Advance Payment Invoice"

    advance_payment_method = fields.Selection(
        selection=[
            ('delivered', "Regular invoice"),
            ('percentage', "Down payment (percentage)"),
            ('fixed', "Down payment (fixed amount)"),
            ('select_lines', "Select lines to bill"),
        ],
        string="Create Bill",
        default='delivered',
        required=True,
        help="A standard bill is issued with all the order lines ready for invoicing.")
    
    count = fields.Integer(string="Order Count", compute='_compute_count')
    purchase_order_ids = fields.Many2many(
        'purchase.order', default=lambda self: self.env.context.get('active_ids'))

    # Down Payment logic
    has_down_payments = fields.Boolean(
        string="Has down payments", compute="_compute_has_down_payments")
    deduct_down_payments = fields.Boolean(string="Deduct down payments", default=True)

    # New Down Payment
    amount = fields.Float(
        string="Down Payment",
        help="The percentage of amount to be invoiced in advance.")
    fixed_amount = fields.Monetary(
        string="Down Payment Amount (Fixed)",
        help="The fixed amount to be invoiced in advance.")
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
        store=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        compute='_compute_company_id',
        store=True)
    amount_invoiced = fields.Monetary(
        string="Already invoiced",
        compute="_compute_invoice_amounts",
        help="Only confirmed down payments are considered.")

    # UI
    display_draft_invoice_warning = fields.Boolean(compute="_compute_display_draft_invoice_warning")
    
    # Custom Lines for "Select Lines"
    custom_line_ids = fields.One2many('purchase.advance.payment.inv.line', 'wizard_id', string="Custom Line Details")

    # === COMPUTE METHODS === #

    @api.depends('purchase_order_ids')
    def _compute_count(self):
        for wizard in self:
            wizard.count = len(wizard.purchase_order_ids)

    @api.depends('purchase_order_ids')
    def _compute_has_down_payments(self):
        for wizard in self:
            wizard.has_down_payments = bool(
                wizard.purchase_order_ids.order_line.filtered('is_downpayment')
            )

    @api.depends('purchase_order_ids')
    def _compute_currency_id(self):
        self.currency_id = False
        for wizard in self:
            if wizard.count == 1:
                wizard.currency_id = wizard.purchase_order_ids.currency_id

    @api.depends('purchase_order_ids')
    def _compute_company_id(self):
        self.company_id = False
        for wizard in self:
            if wizard.count == 1:
                wizard.company_id = wizard.purchase_order_ids.company_id

    @api.depends('purchase_order_ids')
    def _compute_display_draft_invoice_warning(self):
        for wizard in self:
            invoice_states = wizard.purchase_order_ids._origin.sudo().invoice_ids.mapped('state')
            wizard.display_draft_invoice_warning = 'draft' in invoice_states

    @api.depends('purchase_order_ids')
    def _compute_invoice_amounts(self):
        for wizard in self:
            wizard.amount_invoiced = sum(wizard.purchase_order_ids._origin.mapped('amount_invoiced'))

    # === ONCHANGE METHODS ===#

    @api.onchange('advance_payment_method')
    def _onchange_advance_payment_method(self):
        if self.advance_payment_method == 'percentage':
            amount = self.default_get(['amount']).get('amount')
            self.amount = amount if amount else 0.0
            
        if self.advance_payment_method == 'select_lines' and self.purchase_order_ids:
            lines = []
            for order in self.purchase_order_ids:
                order_line = order.order_line.filtered(lambda m: not m.display_type and m.qty_to_invoice > 0)
                for line in order_line:
                    lines.append((0, 0, {
                        'purchase_line_id': line.id,
                        'qty_to_invoice': line.qty_to_invoice,
                    }))
            self.custom_line_ids = lines
        else:
            self.custom_line_ids = False

    # === CONSTRAINT METHODS === #

    def _check_amount_is_positive(self):
        for wizard in self:
            if wizard.advance_payment_method == 'percentage' and wizard.amount <= 0.00:
                raise UserError(_('The value of the down payment amount must be positive.'))
            if wizard.advance_payment_method == 'fixed' and wizard.fixed_amount <= 0.00:
                raise UserError(_('The value of the down payment amount must be positive.'))

    # === ACTION METHODS === #

    def create_invoices(self):
        self._check_amount_is_positive()
        invoices = self._create_invoices(self.purchase_order_ids)
        return self.purchase_order_ids.action_view_invoice(invoices=invoices)

    def view_draft_invoices(self):
        return {
            'name': _('Draft Bills'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'views': [(False, 'list'), (False, 'form')],
            'res_model': 'account.move',
            'domain': [('line_ids.purchase_line_id.order_id', 'in', self.purchase_order_ids.ids), ('state', '=', 'draft')],
        }

    # === BUSINESS METHODS === #

    def _create_invoices(self, purchase_orders):
        self.ensure_one()

        # 1. Custom Select Lines Logic
        if self.advance_payment_method == 'select_lines':
            selected_lines = self.custom_line_ids.filtered(lambda l: l.is_select)
            if not selected_lines:
                raise ValidationError(_("Please select at least one line to bill."))

            invoices = self.env['account.move']
            for order in purchase_orders:
                move_vals = order._prepare_invoice()
                move_vals['invoice_line_ids'] = []
                
                order_selected_lines = selected_lines.filtered(lambda m: m.purchase_line_id.order_id == order)
                for wiz_line in order_selected_lines:
                    if wiz_line.qty_to_invoice > 0:
                        line_vals = wiz_line.purchase_line_id._prepare_account_move_line()
                        line_vals['quantity'] = wiz_line.qty_to_invoice
                        move_vals['invoice_line_ids'].append((0, 0, line_vals))
                
                if move_vals['invoice_line_ids']:
                    invoices |= self.env['account.move'].sudo().create([move_vals])
            return invoices

        # 2. Regular Invoice Logic (Odoo core Purchase fallback)
        if self.advance_payment_method == 'delivered':
            invoices = self.env['account.move']
            for order in purchase_orders:
                move_vals = order._prepare_invoice()
                move_vals['invoice_line_ids'] = []
                for line in order.order_line:
                    if line.qty_to_invoice > 0:
                        move_vals['invoice_line_ids'].append((0, 0, line._prepare_account_move_line()))
                invoices |= self.env['account.move'].sudo().create([move_vals])
            return invoices

        # 3. Down Payment Logic (Copied directly from Odoo 19 Sale Core)
        else:
            self.purchase_order_ids.ensure_one()
            self = self.with_company(self.company_id)
            order = self.purchase_order_ids

            AccountTax = self.env['account.tax']
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)

            if self.advance_payment_method == 'percentage':
                amount_type = 'percent'
                amount = self.amount
            else:
                amount_type = 'fixed'
                amount = self.fixed_amount

            down_payment_base_lines = AccountTax._prepare_down_payment_lines(
                base_lines=base_lines,
                company=self.company_id,
                amount_type=amount_type,
                amount=amount,
                computation_key=f'down_payment,{self.id}',
            )

            # Update the purchase order.
            order._create_down_payment_section_line_if_needed()
            po_lines = order._create_down_payment_lines_from_base_lines(down_payment_base_lines)

            # Create the invoice.
            invoice_values = self.with_context(accounts=[
                base_line['account_id'] or self._get_down_payment_account(base_line.get('product_id'))
                for base_line in down_payment_base_lines
            ])._prepare_down_payment_invoice_values(
                order=order,
                po_lines=po_lines,
            )
            invoice_sudo = self.env['account.move'].sudo().create(invoice_values)

            invoice = invoice_sudo.sudo(self.env.su)
            poster = (self.env.user._is_internal() and self.env.user.id) or SUPERUSER_ID
            invoice.with_user(poster).message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': invoice, 'origin': order},
                subtype_xmlid='mail.mt_note',
            )

            title = _("Down payment bill")
            order.with_user(poster).message_post(
                body=_("%s has been created", invoice._get_html_link(title=title)),
            )

            return invoice

    def _prepare_down_payment_invoice_values(self, order, po_lines):
        self.ensure_one()
        accounts = self.env.context.get('accounts', [])
        return {
            **order._prepare_invoice(),
            'invoice_line_ids': [
                Command.create(self._prepare_down_payment_invoice_line_values(order, po_line, account))
                for po_line, account in zip(po_lines, accounts)
            ],
        }

    def _prepare_down_payment_invoice_line_values(self, order, po_line, account):
        self.ensure_one()
        self = self.with_context(lang=order.partner_id.lang)

        if self.advance_payment_method == 'percentage':
            name = self.env._("Down payment of %s%%", formatLang(self.env, self.amount))
        else:
            name = self.env._("Down Payment")

        line_vals = po_line._prepare_account_move_line()
        line_vals.update({
            'name': name,
            'quantity': 1.0,
        })
        if account:
            line_vals['account_id'] = account.id if hasattr(account, 'id') else account
            
        return line_vals

    def _get_down_payment_account(self, product):
        if not product:
            return None
        product_account = product.product_tmpl_id.get_product_accounts(
            fiscal_pos=self.purchase_order_ids.fiscal_position_id
        )
        return product_account.get('expense')
