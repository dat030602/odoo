from odoo import models, fields, api, _

class VietQRBankConfig(models.Model):
    _name = 'vietqr.bank.config'
    _description = 'VietQR Bank Config'

    name = fields.Char('Name', required=True)
    vietqr_bank_id = fields.Many2one('vietqr.bank', string="Bank", required=True)
    template_code = fields.Char('Template Code', required=True)
    is_default = fields.Boolean('Default', default=False)
    partner_bank_id = fields.Many2one('res.partner.bank', string="Bank Account", required=True)
    
    def _get_qr_url(self, order):
        bank_bin = self.vietqr_bank_id.bin
        account_number = self.partner_bank_id.acc_number
        template_code = self.template_code
        qr_url = f"https://api.vietqr.io/image/{bank_bin}-{account_number}-{template_code}.jpg?amount={order.amount_total}&addInfo={order.bank_info if order.bank_info else ''}"
        return qr_url
                
    def create_vietqr_qr_code(self, order):
        self.ensure_one()
        if order:
            qr_url = self._get_qr_url(order)

            order.write({
                'qr_url': qr_url
            })

            self.env['mail.message'].sudo().create({
                'model': order._name,
                'res_id': order.id,
                'message_type': 'comment',
                'body': f'<p>{_("QR code has been created with information:")}</p><img src="{qr_url}" width="200px" alt="QR Code"/>',
            })

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

