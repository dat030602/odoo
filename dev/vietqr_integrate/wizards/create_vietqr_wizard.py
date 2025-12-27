from odoo import models, fields, api, _

class CreateVietQRWizard(models.TransientModel):
    _name = 'create.vietqr.wizard'
    _description = 'Wizard to Create Sepay QR Code'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True)

    amount = fields.Monetary(string='Amount')
    bank_id = fields.Many2one('vietqr.bank', string='Bank')
    description = fields.Char(string='Description', default='Payment for Sale Order')
    currency_id = fields.Many2one('res.currency', string='Currency')

    def default_get(self, fields):
        res = super(CreateVietQRWizard, self).default_get(fields)
        bank = self.env['vietqr.bank'].search([('is_default', '=', True)], limit=1)
        if bank:
            res.update({
                'bank_id': bank.id,
            })
        res.update({
            'sale_order_id': self.env.context.get('active_id', False),
        })
        return res

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        if self.sale_order_id:
            self.amount = self.sale_order_id.amount_total
            self.currency_id = self.sale_order_id.currency_id
            self.description = self.sale_order_id.name

    def action_create(self):
        self.ensure_one()
        if not self.bank_id:
            raise ValueError(_('Please select a Sepay Bank Config.'))
        qr_code = self.bank_id._get_qr_url(amount=self.amount, description=self.description)
        self.env['mail.message'].sudo().create({
            'model': self.sale_order_id._name,
            'res_id': self.sale_order_id.id,
            'message_type': 'comment',
            'body': f'<p>{_("QR code has been created with information:")}</p><img src="{qr_code}" width="200px" alt="QR Code"/>',
        })
        return
