from odoo import models, fields, api, _
import urllib.parse

class SepayBank(models.Model):
    _name = 'sepay.bank'
    _description = 'Sepay Bank'

    name = fields.Char('Name', required=True)
    sepay_bank_id = fields.Many2one('sepay.bank.config', string="Bank", required=True)
    template = fields.Selection([
        ('compact', 'Compact'),
        ('qronly', 'QR Only'),
    ], string='Template', default='')
    is_default = fields.Boolean('Default', default=False)
    partner_bank_id = fields.Many2one('res.partner.bank', string="Bank Account", required=True)
    
    def _get_qr_url(self, **kwargs):
        """Generate Sepay QR URL"""
        account_number = self.partner_bank_id.acc_number
        bank_code = self.sepay_bank_id.code or self.sepay_bank_id.short_name
        amount = int(kwargs.get('amount')) if kwargs.get('amount') else None
        description = kwargs.get('description', '')
        
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

