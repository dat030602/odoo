from odoo import models, fields, api, _
from unidecode import unidecode
import re

def clean_text(text):
    text = unidecode(text)
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

class CreateVietQRWizard(models.TransientModel):
    _name = 'create.vietqr.wizard'
    _description = 'Wizard to Create VietQR Code'

    resource_id = fields.Integer(string='Resource ID', default=lambda self: self.env.context.get('active_id', False))
    resource_model = fields.Char(string='Resource Model', default=lambda self: self.env.context.get('active_model', False))

    amount = fields.Monetary(string='Amount')
    bank_id = fields.Many2one('vietqr.bank', string='Bank')
    description = fields.Char(string='Description', default='Payment for Sale Order')
    currency_id = fields.Many2one('res.currency', string='Currency')

    def default_get(self, fields):
        res = super(CreateVietQRWizard, self).default_get(fields)
        bank = self.env['vietqr.bank'].search([('is_default', '=', True)], limit=1)
        if bank:
            res.update({'bank_id': bank.id})
        return res

    @api.onchange('resource_id', 'resource_model')
    def _onchange_resource_id(self):
        if self.resource_id and self.resource_model:
            model = self.env[self.resource_model]
            record = model.browse(self.resource_id)
            if getattr(record, 'amount_total', False):
                self.amount = record.amount_total
            if getattr(record, 'currency_id', False):
                self.currency_id = record.currency_id
            if getattr(record, 'ref', False):
                self.description = clean_text(record.ref or '')
            elif getattr(record, 'name', False):
                self.description = clean_text(record.name or '')

    def action_create(self):
        self.ensure_one()
        if not self.bank_id:
            raise ValueError(_('Please select a Bank Config.'))
        qr_code = self.bank_id._get_qr_url(amount=self.amount, description=self.description)
        self.env['mail.message'].sudo().create({
            'model': self.resource_model,
            'res_id': self.resource_id,
            'message_type': 'comment',
            'body': f'<p>{_("QR code has been created with information:")}</p><img src="{qr_code}" width="200px" alt="QR Code"/>',
        })
        return
