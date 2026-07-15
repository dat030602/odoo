# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class DetailsPurchaseBook(models.Model):
    _name = 'details.purchase.book'
    _description = 'Sổ chi tiết mua hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _order = 'id desc'

    name = fields.Char('Tên')
    date_from = fields.Date('Từ ngày', default=date.today())
    date_to = fields.Date('Đến ngày', default=date.today())
    creator_id = fields.Many2one('res.users', string='Người lập biểu')
    commercial_department_id = fields.Many2one('res.users', string='Phòng thương mại')
    accountant_id = fields.Many2one('res.users', string='Phòng kế toán')
    accountant_chief_id = fields.Many2one('res.users', string='Kế toán trưởng')
    unit_head_id = fields.Many2one('res.users', string='Thủ trưởng đơn vị')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Kho')
    line_ids = fields.One2many('details.purchase.book.line', 'parent_id', string='Chi tiết')
    active = fields.Boolean('Hoạt động', default=True)
    currency_id = fields.Many2one('res.currency', string='Đơn vị tiền tệ', default=lambda self: self.env.company.currency_id)

    state = fields.Selection(
        [('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'), ('refuse', 'Từ chối'), ('cancel', 'Hủy')],
        'Trạng thái', default="draft", tracking=True)

    trp_approve_history_ids = fields.One2many('trp.approve.history', 'dsk_purchase_book_id', string='Lịch sử duyệt', copy=False)

    def unlink(self):
        for record in self:
            if record.state not in ['refuse', 'cancel', 'draft']:
                raise UserError("Không thể xóa yêu cầu ký đã duyệt!")
        return super(DetailsPurchaseBook, self).unlink()

    def action_cancel(self):
        self.write({'state': 'cancel'})
        res_history = self.trp_approve_history_ids
        self.env['mail.activity'].search([('trp_approve_history_id', 'in', res_history.ids)]).with_context(skip_approve_done=True).action_done()

    def action_undo(self):
        self.write({'state': 'draft'})

    def action_sign(self):
        self = self.sudo()
        if not self.line_ids:
            raise ValidationError("Vui lòng lấy dữ liệu trước khi trình duyệt!")
        res_approve = {}
        if not self.trp_approve_config_line_id and self.state in ('draft'):
            self.approve_next_action = 'action_sign'
            self.approve_state_init = self.state
            self.approve_state_next = 'approve'
            res_approve = self.with_context(approve_type='new').create_approve()
        if not res_approve or not self.trp_approve_config_line_id:
            if self.state == 'approve':
                self.update({'state': 'approved'})
                return

    def action_agree(self):
        res = super(DetailsPurchaseBook, self).action_agree()
        for record in self:
            if record.state == 'approved':
                try:
                    report_pdf = self.env['ir.actions.report']._render_qweb_pdf(
                        "biz_details_purchase_report.action_details_purchase_book_pdf", record.id)
                    record.message_post(
                        body=f"Sổ chi tiết mua hàng {record._get_html_link()}",
                        attachments=[(f'{record.name}.pdf', report_pdf[0])],
                    )
                except Exception:
                    record.message_post(
                        body=f"Sổ chi tiết mua hàng {record._get_html_link()} đã được duyệt.",
                    )
        return res

    def action_print_pdf(self):
        return self.env.ref('biz_details_purchase_report.action_details_purchase_book_pdf').report_action(self)

    def action_print_excel(self):
        return self.env.ref('biz_details_purchase_report.action_details_purchase_book_xlsx').report_action(self)

    @api.model
    def default_get(self, fields_list):
        defaults = super(DetailsPurchaseBook, self).default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()
        chief_finance_id = env_params.get_param('biz_details_purchase_report.chief_accountant_id', False)
        accountant_id = env_params.get_param('biz_details_purchase_report.accountant_id', False)
        director_id = env_params.get_param('biz_details_purchase_report.director_id', False)
        commercial_id = env_params.get_param('biz_details_purchase_report.commercial_department_id', False)
        date_from = date.today().strftime("%d%m%Y")
        date_to = date.today().strftime("%d%m%Y")
        defaults.update({
            'creator_id': self.env.user.id,
            'commercial_department_id': int(commercial_id) if commercial_id else False,
            'accountant_chief_id': int(chief_finance_id) if chief_finance_id else False,
            'accountant_id': int(accountant_id) if accountant_id else False,
            'unit_head_id': int(director_id) if director_id else False,
            'name': f'Mua hàng {date_from} - {date_to}',
        })
        return defaults

    @api.onchange('date_from', 'date_to', 'warehouse_ids')
    def _onchange_dates(self):
        for record in self:
            date_from = record.date_from.strftime('%d%m%Y') if record.date_from else ''
            date_to = record.date_to.strftime('%d%m%Y') if record.date_to else ''
            warehouse_names = ', '.join(record.warehouse_ids.mapped('name')) if record.warehouse_ids else ''
            if date_from and date_to:
                if date_from == date_to:
                    name = f'Mua hàng ngày {date_from}'
                else:
                    name = f'Mua hàng {date_from} - {date_to}'
                if warehouse_names:
                    name += f' - {warehouse_names}'
                record.name = name

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError("'Đến ngày' phải lớn hơn hoặc bằng 'Từ ngày'.")

    def action_confirm(self):
        self = self.with_context(tz=self.env.user.tz).sudo()
        self.ensure_one()
        self.line_ids.unlink()

        StockMove = self.env['stock.move'].with_context(tz=self.env.user.tz).sudo()
        domain = [
            ('purchase_line_id', '!=', False),
            ('location_id.usage', '=', 'supplier'),
            ('state', '=', 'done')
        ]
        if self.date_from:
            date_from = datetime.combine(self.date_from, datetime.min.time()) - timedelta(hours=7)
            domain.append(('date', '>=', date_from))
        if self.date_to:
            date_to = datetime.combine(self.date_to, datetime.max.time()) - timedelta(hours=7)
            domain.append(('date', '<=', date_to))
        if self.warehouse_ids:
            domain += ['|', ('location_id.warehouse_id', 'in', self.warehouse_ids.ids),
                       ('location_dest_id.warehouse_id', 'in', self.warehouse_ids.ids)]

        StockMoves = StockMove.search(domain, order='date asc')

        line_vals = []
        for line in StockMoves:
            quantity = line.quantity_done or 0
            purchase_line = line.purchase_line_id
            order = purchase_line.order_id if purchase_line else False
            invoice_lines = purchase_line.invoice_lines.filtered(lambda inv_line: inv_line.move_id.move_type == 'in_invoice') if purchase_line else self.env['account.move.line']
            move_ids = self.env['account.move']
            for move in invoice_lines.move_id:
                if not any([True for move_line in move.line_ids if move_line.account_id.account_type in ['expense', 'expense_depreciation', 'expense_direct_cost']]):
                    move_ids |= move
            invoice_lines = move_ids.line_ids.filtered(lambda mv_line: mv_line in purchase_line.invoice_lines) if purchase_line else self.env['account.move.line']

            currency = order.currency_id if order else False
            currency_name = currency.name if currency else ''
            exchange_rate = unit_price_nt = unit_price = purchase_value = purchase_value_nt = 0
            account_debit = ''
            account_credit = ''

            if purchase_line:
                price_unit = purchase_line.price_unit
                if currency_name == 'VND':
                    unit_price = price_unit
                    purchase_value_nt = unit_price_nt * quantity
                    purchase_value = unit_price * quantity
                else:
                    unit_price_nt = price_unit
                    purchase_value_nt = unit_price_nt * quantity
                    if order and order.apply_manual_currency_exchange:
                        exchange_rate = order.inverse_manural_currency_exchange_rate
                    else:
                        date_approve = order.date_approve and order.date_approve.date() or False
                        if date_approve:
                            rate_before = currency.rate_ids.filtered(lambda r: r.name <= date_approve).sorted('name', reverse=True)[:1]
                            if rate_before:
                                exchange_rate = rate_before.inverse_company_rate
                    unit_price = unit_price_nt * exchange_rate
                    purchase_value = purchase_value_nt * exchange_rate

            if invoice_lines:
                account_debit = invoice_lines.mapped('account_id.code')[0] if invoice_lines.mapped('account_id.code') else ''
                account_credit = invoice_lines.mapped('ctp_account_ids.code')[0] if invoice_lines.mapped('ctp_account_ids.code') else ''
            else:
                account_move_ids = line.account_move_ids.filtered(lambda x: x.state == 'posted')
                line_debit_ids = account_move_ids.line_ids.filtered(lambda x: x.debit > 0)
                line_credit_ids = account_move_ids.line_ids.filtered(lambda x: x.credit > 0)
                account_debit = line_debit_ids.mapped('account_id.code')[0] if line_debit_ids else ''
                account_credit = line_credit_ids.mapped('account_id.code')[0] if line_credit_ids else ''

            date_value = line.date and (line.date + timedelta(hours=7)).date() or False

            line_vals.append({
                'parent_id': self.id,
                'date': date_value,
                'name': line.reference or '',
                'partner_name': purchase_line and purchase_line.partner_id.name or '',
                'product_code': line.product_id and line.product_id.default_code or '',
                'product_name': line.product_id and line.product_id.name or '',
                'product_uom_id': line.product_uom and line.product_uom.name.upper() or '',
                'quantity': quantity,
                'exchange_rate': exchange_rate,
                'unit_price_nt': unit_price_nt,
                'unit_price': unit_price,
                'purchase_value_nt': purchase_value_nt,
                'purchase_value': purchase_value,
                'location_dest_id': line.location_dest_id and line.location_dest_id.location_id.name or '',
                'account_debit': account_debit,
                'account_credit': account_credit,
                'order_name': line.origin or '',
            })

        if line_vals:
            self.env['details.purchase.book.line'].create(line_vals)

    def action_view_details(self):
        self.ensure_one()
        action = self.env.ref('biz_details_purchase_report.action_details_purchase_book_line').sudo().read()[0]
        action['domain'] = [('parent_id', '=', self.id)]
        return action
