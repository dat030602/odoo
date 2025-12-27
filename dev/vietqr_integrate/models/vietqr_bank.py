from odoo import models, fields, api, _

class VietQRBank(models.Model):
    _name = 'vietqr.bank'
    _description = 'VietQR Bank'

    name = fields.Char('Name', required=True)
    vietqr_bank_id = fields.Many2one('vietqr.bank.config', string="Bank", required=True)
    template_type = fields.Selection([
        ('compact', 'Compact'),
        ('compact2', 'Compact 2'),
        ('qr_only', 'QR Only'),
        ('print', 'Print'),
        ('custom', 'Custom'),
    ], string="Template Type", required=True, default='compact')
    template_code = fields.Char('Template Code')
    is_default = fields.Boolean('Default', default=False)
    partner_bank_id = fields.Many2one('res.partner.bank', string="Bank Account", required=True)
    
    def _get_qr_url(self, **kwargs):
        bank_bin = self.vietqr_bank_id.bin
        account_number = self.partner_bank_id.acc_number
        if self.template_type == 'custom':
            template_code = self.template_code
        else:
            template_code = self.template_type
        qr_url = f"https://api.vietqr.io/image/{bank_bin}-{account_number}-{template_code}.jpg?amount={kwargs.get('amount', 0)}&addInfo={kwargs.get('description','')}"
        return qr_url

    def action_test_qr(self):
        self.ensure_one()
        bank_bin = self.vietqr_bank_id.bin
        account_number = self.partner_bank_id.acc_number
        qr_url = f"https://api.vietqr.io/image/{bank_bin}-{account_number}-{self.template_code}.jpg?amount={20000}&addInfo=Test"
        return {
            "type": "ir.actions.act_url",
            "url": qr_url,
            "target": "self",
        }

