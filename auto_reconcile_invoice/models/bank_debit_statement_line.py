# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class BankDebitStatementLine(models.Model):
    _name = 'bank.debit.statement.line'
    _description = 'Số dư nợ ngân hàng'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Mã', 
        required=True, 
        copy=False, 
        readonly=True, 
        index=True, 
        default=lambda self: _('New')
    )
    ref = fields.Text(string='Nội dung giao dịch', readonly=True)
    amount = fields.Monetary(string='Số tiền', tracking=True)
    date = fields.Date(string='Ngày giao dịch', default=fields.Date.context_today, tracking=True)
    transaction_number = fields.Char("Số giao dịch")
    counterpart_account = fields.Char("Tài khoản đối ứng")
    counterpart_name = fields.Char("Tên tài khoản đối ứng")
    partner_bank_id = fields.Many2one("res.partner.bank", string="Tài khoản đối ứng")
    partner_bank_name = fields.Char(
        string='Ngân hàng đối ứng',
        compute='_compute_partner_bank_name',
        store=False
    )
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id)
    journal_id = fields.Many2one('account.journal', string='Sổ nhật ký', domain="[('type', 'in', ('bank', 'cash'))]", tracking=True)

    sale_ids = fields.Many2many('sale.order', string='Đơn hàng')
    partner_ids = fields.Many2many('res.partner', string='Khách hàng', compute='_compute_partner_ids', store=True)

    sale_show_ids = fields.Many2many('sale.order', 'bank_debit_statement_line_sale_order_show_rel', string='Đơn hàng', compute='_compute_partner_show_ids', store=True)
    partner_show_ids = fields.Many2many('res.partner', 'bank_debit_statement_line_res_partner_show_rel', string='Khách hàng', compute='_compute_partner_show_ids', store=True)
    viettel_inv_ids = fields.Many2many('viettel.sinvoice', string='Hóa đơn Viettel', compute='_compute_partner_show_ids', store=True)

    invoice_ids = fields.Many2many(
        'account.move', 
        string='Hóa đơn',
        compute='_compute_invoice_ids',
        store=True
    )

    inv_count = fields.Integer(string='Số hóa đơn', compute='_compute_inv_count')

    payment_ids = fields.Many2many('account.payment', string='Phiếu thanh toán')

    state = fields.Selection([
        ('new', 'Mới'),
        ('payment', 'Đã thanh toán'),
        ('reconciled', 'Đã đối soát'),
        ('cancel', 'Đã hủy')
    ], string='Trạng thái', compute='_compute_state', store=True, default='new', tracking=True)

    line_ids = fields.One2many('bank.debit.statement.partner.line', 'parent_id', string='Dòng sổ phụ')

    count_line_ids = fields.Integer(string='Số dòng sổ phụ', compute='_compute_count_line_ids')

    @api.constrains('partner_ids')
    def _check_partner_ids(self):
        for rec in self:
            if len(rec.partner_ids) > 1:
                raise UserError(_("Chỉ được chọn 1 khách hàng !!!"))

    @api.depends('sale_ids', 'line_ids.sale_ids', 'payment_ids.reconciled_invoice_ids')
    def _compute_partner_show_ids(self):
        for rec in self:
            rec.partner_show_ids = [(6, 0, rec.partner_ids.ids + rec.line_ids.mapped('partner_id').ids)]
            rec.sale_show_ids = [(6, 0, rec.sale_ids.ids + rec.line_ids.mapped('sale_ids').ids)]
            rec.viettel_inv_ids = [(6, 0, rec.payment_ids.mapped('reconciled_invoice_ids.sinvoice_ids').ids)]

    @api.depends('counterpart_account', 'partner_ids', 'partner_show_ids')
    def _compute_partner_bank_name(self):
        for rec in self:
            bank_name = _("Khách hàng chưa cập nhật ngân hàng")
            partner = rec.partner_ids[0] if rec.partner_ids else (rec.partner_show_ids[0] if rec.partner_show_ids else False)
            if partner and rec.counterpart_account:
                clean_account = rec.counterpart_account.strip().replace(" ", "")
                if clean_account:
                    matched_bank = partner.bank_ids.filtered(
                        lambda b: b.acc_number and (clean_account in b.acc_number.replace(" ", "") or b.acc_number.replace(" ", "") in clean_account)
                    )
                    if matched_bank and matched_bank[0].bank_id:
                        bank_name = matched_bank[0].bank_id.name
            rec.partner_bank_name = bank_name

    @api.depends('line_ids')
    def _compute_count_line_ids(self):
        for rec in self:
            rec.count_line_ids = len(rec.line_ids)

    @api.constrains('line_ids', 'amount')
    def _check_line_ids_amount(self):
        for rec in self:
            tong = sum(line.amount for line in rec.line_ids)
            if tong > rec.amount:
                raise UserError('Tổng số tiền trên các dòng sổ phụ không được vượt quá số tiền trên sổ phụ.')
    
    @api.model
    def default_get(self, fields_list):
        defaults = super(BankDebitStatementLine, self).default_get(fields_list)
        defaults['journal_id'] = self.env['account.journal'].search([('name','like','110002630105')], limit=1).id
        return defaults

    @api.depends('payment_ids', 'payment_ids.reconciled_invoice_ids')
    def _compute_invoice_ids(self):
        """
        Tự động lấy danh sách hóa đơn từ phiếu thanh toán đã liên kết.
        """
        for rec in self:
            payment_ids = rec.payment_ids.filtered(lambda p: p.state == 'posted')
            if payment_ids:
                # Lấy tất cả invoice_ids từ các payment và flatten thành list đơn giản
                invoice_ids = []
                for payment in payment_ids:
                    if payment.reconciled_invoice_ids:
                        invoice_ids.extend(payment.reconciled_invoice_ids.ids)
                # Loại bỏ duplicate và gán vào field
                rec.invoice_ids = [(6, 0, list(set(invoice_ids)))]
            else:
                # Nếu không có payment, danh sách hóa đơn sẽ trống
                rec.invoice_ids = [(6, 0, [])]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bank.debit.statement.line') or _('New')
        return super().create(vals_list)
    
    def write(self, vals):
        res = super().write(vals)
        if 'payment_ids' in vals:
            payment_ids = vals.get('payment_ids', [])
            payments = self.env['account.payment'].browse([pid[1] for pid in payment_ids if isinstance(pid, tuple) and pid[0] == 4])
            self._post_message_on_payment(payments)
        return res

    @api.depends('sale_ids')
    def _compute_partner_ids(self):
        """
        Tự động cập nhật khách hàng dựa trên đơn hàng được chọn.
        """
        for rec in self:
            partners = rec.sale_ids.mapped('partner_id')
            rec.partner_ids = [(6, 0, partners.ids)]

    @api.depends('invoice_ids')
    def _compute_inv_count(self):
        """
        Đếm số lượng hóa đơn đã liên kết.
        """
        for rec in self:
            rec.inv_count = len(rec.invoice_ids)
            
    @api.depends('payment_ids', 'payment_ids.state')
    def _compute_state(self):
        """
        Tính toán trạng thái dựa trên phiếu thanh toán:
        - Mới: Chưa có phiếu thanh toán.
        - Đã thanh toán: Có phiếu thanh toán đã được ghi sổ (posted).
        - Đã đối soát: Phiếu thanh toán đã được đối soát.
        """
        for rec in self:
            payment_ids = rec.payment_ids.filtered(lambda p: p.state != 'cancel')
            if not payment_ids:
                rec.state = 'new'
            elif all([payment.is_reconciled for payment in payment_ids]):
                rec.state = 'reconciled'
            elif any([payment.state == 'posted' for payment in payment_ids]):
                 rec.state = 'payment'
            else:
                rec.state = 'new'

    def _post_message_on_payment(self, payment_ids):
        odoobot = self.env.ref('base.partner_root').sudo()
        msg = 'Thanh toán được tạo từ %s' % self._get_html_link()
        for payment in payment_ids:
            payment.message_post(body=msg,message_type='comment',subtype_xmlid='mail.mt_note',author_id=odoobot.id)

    def action_delete_account_payment(self):
        """Chuyển trạng thái của dòng sổ phụ thành 'Mới'."""
        self = self.sudo()
        for rec in self:
            payments = rec.payment_ids.filtered(lambda p: p.state != 'cancel')
            for payment in payments:
                if payment.state == 'posted':
                    payment.action_draft()
                payment.action_cancel()
        return

    def action_cancel(self):
        """Chuyển trạng thái của dòng sổ phụ thành 'Đã hủy'."""
        # Lưu ý: Hàm này không hủy phiếu thanh toán liên quan.
        # Đó là một hành động người dùng cần làm thủ công nếu cần.
        return self.write({'state': 'cancel'})

    def action_create_payment(self):
        """
        Tạo phiếu thanh toán nhóm theo khách hàng.
        """
        self.ensure_one()
        # Sửa điều kiện: chỉ cho phép dòng ở trạng thái 'Mới'
        if any(rec.state != 'new' for rec in self):
            raise UserError(_("Chỉ những dòng ở trạng thái 'Mới' mới có thể tạo thanh toán."))

        partners = self.mapped('partner_ids')
        payment_obj = self.env['account.payment']
        journal = self.journal_id
        if not journal:
            raise UserError(_("Vui lòng chọn Sổ nhật ký trước khi tạo thanh toán."))
        
        if not self.partner_ids and not self.line_ids:
            raise UserError(_("Khách hàng không được để trống !!!"))

        if not self.line_ids:
            for partner in partners:
                payment_vals = {
                    'date': self.date,
                    'partner_id': partner.id,
                    'amount': self.amount,
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'journal_id': journal.id,
                    'sale_ids': [(6, 0, self.mapped('sale_ids').ids)],
                }
                payment = payment_obj.create(payment_vals)
                payment.action_post()
                
                # Cập nhật state thành 'Đã thanh toán' sau khi tạo phiếu
                self.write({
                    'payment_ids': [(4, payment.id)],
                    # 'state': 'payment'
                })
        else:
            for line in self.line_ids:
                payment_vals = {
                    'date': line.date,
                    'partner_id': line.partner_id.id,
                    'amount': line.amount,
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'journal_id': journal.id,
                    'sale_ids': [(6, 0, line.mapped('sale_ids').ids)],
                }
                payment = payment_obj.create(payment_vals)
                payment.action_post()
                self.write({
                    'payment_ids': [(4, payment.id)],
                    # 'state': 'payment'
                })
    
    def action_view_invoices(self):
        """
        Cập nhật: Mở form view nếu chỉ có 1 hóa đơn,
        mở tree view nếu có nhiều hơn 1 hoặc không có hóa đơn nào.
        """
        self.ensure_one()
        invoices = self.invoice_ids

        # Mặc định là action xem danh sách (tree view)
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Hóa đơn',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoices.ids)],
            'target': 'current',
        }

        # Nếu chỉ có chính xác 1 hóa đơn, ta sửa lại action để xem thẳng form view
        if len(invoices) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = invoices.id
            # Xóa domain đi vì không cần thiết khi đã có res_id
            del action['domain']
        
        return action

    def action_view_payment(self):
        """
        Mở form view của phiếu thanh toán đã được liên kết.
        """
        self.ensure_one()
        payments = self.payment_ids
        if len(payments) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Phiếu thanh toán',
                'res_model': 'account.payment',
                'view_mode': 'form',
                'res_id': payments.id,
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Phiếu thanh toán',
                'res_model': 'account.payment',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
                'target': 'current',
            }
