from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'currency.rate.mixin']

    def _get_rate_context(self):
        self.ensure_one()
        rate_date = (self.date_order or fields.Datetime.now()).date()
        return (self.company_id.currency_id, self.currency_id, self.company_id, rate_date)

    @api.depends(
        'currency_id',
        'date_order',
        'company_id',
        'rate_mode',
        'selected_rate_id',
    )
    def _compute_currency_rate(self):
        super()._compute_currency_rate()
        for order in self:
            if order.currency_id != order.company_id.currency_id and order.rate_mode == 'custom':
                order.currency_rate = order._get_dynamic_rate(auto_rate=order.currency_rate)
