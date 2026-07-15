from odoo import models, fields, api
import requests
import base64
from odoo.tools import image_process
import string
import random
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

def get_image_from_url(url):
    if url:
        response = requests.get(url)
        if response.status_code == 200:
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            return image_base64
    return False

class VietQRBank(models.Model):
    _name = 'vietqr.bank.transaction'
    _description = 'VietQR Bank Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Tên')
    sale_ids = fields.Many2many('sale.order', string='Đơn hàng')
    code = fields.Char('Mã')
    amount = fields.Monetary('Số tiền')
    bank_id = fields.Many2one('vietqr.bank.config', string='Ngân hàng')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id)
    date = fields.Date('Ngày', default=fields.Date.context_today)
    reference = fields.Char('Mã')
    qr_url = fields.Char(string="QR Code URL")
    qr_image = fields.Binary(string="QR Code Image", max_width=200, max_height=200, attachment=False, stored=True, compute="_compute_logo")
    bank_statement_line_ids = fields.Many2many('bank.statement.line', string='Bank Statement Lines')
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled')
    ],string="Trạng thái", compute="_compute_state", store=True)

    @api.constrains('sale_ids')
    def _check_sale_ids(self):
        for rec in self:
            if len(rec.sale_ids.mapped('partner_id')) > 1:
                raise UserError("Tất cả đơn hàng phải thuộc cùng một khách hàng với giao dịch ngân hàng.")
    
    def default_get(self, fields):
        res = super(VietQRBank, self).default_get(fields)
        config = self.env['vietqr.bank.config'].search([('is_default', '=', True)], limit=1)
        res['bank_id'] = config.print_qr_id.id if config and config.print_qr_id else config.id
        res['code'] = self._generate_ref_code(length=10)
        ids = self.env.context.get('active_ids', [])
        if ids and self.env.context.get('active_model') == 'sale.order':
            res['sale_ids'] = [(6, 0, ids)]
        return res

    @api.depends('bank_statement_line_ids.state')
    def _compute_state(self):
        for rec in self:
            states = rec.bank_statement_line_ids.mapped('state')
            if not states:
                rec.state = 'draft'
            elif all(state in ('payment','reconciled') for state in states if state != 'cancelled'):
                rec.state = 'paid'
            elif 'cancelled' in states and len(states) == 1:
                rec.state = 'cancelled'
            else:
                rec.state = 'partial'
    
    @api.depends('qr_url')
    def _compute_logo(self):
        for rec in self:
            qr_image = get_image_from_url(rec.qr_url)
            rec.qr_image = image_process(qr_image) if qr_image else qr_image

    def action_create_bank_statement_line(self, amount=None):
        for rec in self:
            bank_statement_line_obj = self.env['bank.statement.line']
            amount = amount if amount is not None else rec.amount
            sale_ids = rec.sale_ids
            partner_ids = sale_ids.mapped('partner_id')
            bank_statement_line = bank_statement_line_obj.create({
                'name': rec.name,
                'amount': amount,
                'date': rec.date,
                'ref': rec.reference,
                'currency_id': rec.currency_id.id,
                'sale_ids': [(6, 0, sale_ids.ids)],
                'partner_ids': [(6, 0, partner_ids.ids)]
            })
            bank_statement_line.action_create_payment()
            rec.bank_statement_line_ids = [(4, bank_statement_line.id)]
        return True
        
        
    def _generate_ref_code(self, length=4):
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=length))

    def action_generate_ref_code(self):
        for rec in self:
            rec.code = self._generate_ref_code(length=10)
            rec._onchange_code_ref()

    def _get_qr_url(self):
        bank_bin = self.bank_id.vietqr_bank_id.bin
        account_number = self.bank_id.partner_bank_id.acc_number
        template_code = self.bank_id.template_code
        qr_url = f"https://api.vietqr.io/image/{bank_bin}-{account_number}-{template_code}.jpg?amount={self.amount}&addInfo={self.reference if self.reference else ''}"
        return qr_url

    @api.onchange('code')
    def _onchange_code_ref(self):
        for rec in self:
            rec.reference = 'TT %s' % rec.code
            rec.qr_url = rec._get_qr_url()
            rec.message_ids.sudo().create({
                'model': rec._name,
                'res_id': rec.id,
                'message_type': 'comment',
                'body': f'<p>QR code đã được tạo với thông tin:</p><img src="{rec.qr_url}" width="300px" alt="QR Code"/>',
            })
