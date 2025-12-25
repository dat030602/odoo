from odoo import models, fields, api, _
import urllib.parse

class SepayBankConfig(models.Model):
    _name = 'sepay.bank.config'
    _description = 'Sepay Bank Config'

    name = fields.Char('Name', required=True)
    sepay_bank_id = fields.Many2one('sepay.bank', string="Bank", required=True)
    template = fields.Selection([
        ('', 'Default'),
        ('compact', 'Compact'),
        ('qronly', 'QR Only'),
    ], string='Template', default='', required=True)
    is_default = fields.Boolean('Default', default=False)
    partner_bank_id = fields.Many2one('res.partner.bank', string="Bank Account", required=True)
    
    def _get_qr_url(self, order):
        """Generate Sepay QR URL"""
        account_number = self.partner_bank_id.acc_number
        bank_code = self.sepay_bank_id.code or self.sepay_bank_id.short_name
        amount = int(order.amount_total) if order.amount_total else None
        description = order.bank_info if hasattr(order, 'bank_info') and order.bank_info else ''
        
        # Build URL parameters
        params = {
            'acc': account_number,
            'bank': bank_code,
        }
        
        if amount:
            params['amount'] = amount
        
        if description:
            params['des'] = description
        
        if self.template:
            params['template'] = self.template
        
        # Build query string
        query_string = urllib.parse.urlencode(params)
        qr_url = f"https://qr.sepay.vn/img?{query_string}"
        return qr_url
                
    def create_sepay_qr_code(self, order):
        """Create Sepay QR code for order"""
        self.ensure_one()
        if order:
            qr_url = self._get_qr_url(order)

            if hasattr(order, 'qr_url'):
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
        """Test QR code generation"""
        self.ensure_one()
        account_number = self.partner_bank_id.acc_number
        bank_code = self.sepay_bank_id.code or self.sepay_bank_id.short_name
        
        params = {
            'acc': account_number,
            'bank': bank_code,
            'amount': 20000,
            'des': 'Test',
        }
        
        if self.template:
            params['template'] = self.template
        
        query_string = urllib.parse.urlencode(params)
        qr_url = f"https://qr.sepay.vn/img?{query_string}"
        
        return {
            "type": "ir.actions.act_url",
            "url": qr_url,
            "target": "self",
        }

