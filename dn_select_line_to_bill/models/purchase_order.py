# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command, _

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_downpayment = fields.Boolean(string="Is a down payment", default=False)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    amount_invoiced = fields.Monetary(
        string="Amount Invoiced",
        compute='_compute_amount_invoiced',
        help="Sum of invoiced amounts.",
    )

    @api.depends('invoice_ids.state', 'invoice_ids.amount_total')
    def _compute_amount_invoiced(self):
        for order in self:
            invoices = order.invoice_ids.filtered(lambda m: m.state == 'posted' and m.move_type in ('in_invoice', 'in_receipt'))
            order.amount_invoiced = sum(invoices.mapped('amount_total'))

    def dn_action_create_invoice(self):
        # Override to open wizard instead of direct bill creation
        return {
            'name': _('Create Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.advance.payment.inv',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_order_ids': [Command.set(self.ids)],
            },
        }

    # === DOWN PAYMENT HELPER METHODS (Mimicking Sale Order Core 19) === #

    def _create_down_payment_section_line_if_needed(self):
        self.ensure_one()
        if not self.order_line.filtered(lambda m: m.display_type == 'line_section' and m.name == _('Down Payments')):
            self.env['purchase.order.line'].create({
                'order_id': self.id,
                'display_type': 'line_section',
                'name': _('Down Payments'),
            })

    def _create_down_payment_lines_from_base_lines(self, down_payment_base_lines):
        self.ensure_one()
        po_lines = self.env['purchase.order.line']
        for base_line in down_payment_base_lines:
            po_lines |= self.env['purchase.order.line'].create({
                'order_id': self.id,
                'name': _('Down Payment'),
                'product_qty': 1.0,
                'price_unit': base_line['price_unit'],
                'taxes_id': [Command.set(base_line['tax_ids'])],
                'is_downpayment': True,
            })
        return po_lines
