from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PurchasePaymentRequestWizard(models.TransientModel):
    _name = 'purchase.payment.request.wizard'
    _description = 'Popup Đề nghị thanh toán từ Đơn mua hàng'

    purchase_id = fields.Many2one('purchase.order', string='Đơn mua hàng', required=True, readonly=True)
    # partner_id = fields.Many2one('res.partner', string='Đối tượng thanh toán', required=True)
    company_id = fields.Many2one('res.company', string='Công ty', required=True, default=lambda self: self.env.company.id)
    journal_id = fields.Many2one(
        'account.journal',
        string='Sổ nhật kí',
        required=True,
        domain="[('company_id', '=', company_id)]",
    )

    # Hình thức thanh toán: selector với 2 lựa chọn là tiền mặt và chuyển khoản
    payment_type_selector = fields.Selection(
        [
            ('cash', 'Tiền mặt'),
            ('transfer', 'Chuyển khoản'),
        ],
        string='Hình thức thanh toán',
        required=True,
        default='cash',
    )

    bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='Tài khoản ngân hàng',
    )

    beneficiary_name = fields.Char(
        string='Người hưởng thụ',
    )
    amount = fields.Monetary(string='Số tiền', required=True)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', required=True)
    payment_date = fields.Date(string='Ngày', default=fields.Date.context_today, required=True)
    note = fields.Char(string='Nội dung', required=True)

    attachment_ids = fields.Many2many('ir.attachment', string='Chứng từ đính kèm', help='Bắt buộc đính kèm để xác nhận')

    @api.onchange('bank_account_id')
    def _onchange_bank_account_id(self):
        if self.bank_account_id:
            self.beneficiary_name = self.bank_account_id.acc_holder_name
        
    def action_confirm(self):
        self.ensure_one()
        # Require attachments
        if not self.attachment_ids:
            raise ValidationError(_('Vui lòng đính kèm chứng từ trước khi xác nhận.'))

        beneficiary_name = self.beneficiary_name
        if self.bank_account_id:
            beneficiary_name = self.bank_account_id.acc_holder_name

        vals = {
            # 'partner_id': self.partner_id.id,
            'total_amount': self.amount,
            'currency_id': self.currency_id.id,
            'date': self.payment_date,
            'note': self.note,
            'journal_id': self.journal_id.id,
            'type': self.payment_type_selector,
            'partner_bank_id': self.bank_account_id.id,
            'partner_name': beneficiary_name,
            'purchase_id': self.purchase_id.id,
        }
        payment = self.env['payment.request'].with_context(require_attachment=True).create(vals)
        # Thêm payment request này vào trường m2m của purchase order (nếu có)
        if self.purchase_id:
            self.purchase_id.payment_request_ids = [(4, payment.id)]
        # Link attachments to payment
        # Đính kèm file bằng ghi chú (message_post)
        for attachment in self.attachment_ids:
            payment.message_post(
                body=_("Đính kèm chứng từ thanh toán."),
                attachment_ids=[attachment.id]
            )
        # open payment form
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.request',
            'res_id': payment.id,
            'view_mode': 'form',
            'target': 'current',
        }
        print(payment.total_amount)
        return action
