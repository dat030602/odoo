# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class DetailsInternalTfBook(models.Model):
    _name = 'details.internal.tf.book'
    _description = 'Sổ chi tiết nhập hàng tại cảng'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _order = 'id desc'

    name = fields.Char('Tên')
    date_from = fields.Date('Từ ngày', default=date.today())
    date_to = fields.Date('Đến ngày', default=date.today())
    voter_id = fields.Many2one('res.users', string='Người lập')
    accounting_department_id = fields.Many2one('res.users', string='Phòng Kế toán')
    chief_trade_id = fields.Many2one('res.users', string='Phòng Thương mại')
    chief_finance_id = fields.Many2one('res.users', string='Kế toán trưởng')
    director_id = fields.Many2one('res.users', string='Thủ trưởng đơn vị')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Kho')
    line_ids = fields.One2many('details.internal.tf.book.line', 'parent_id', string='Chi tiết')
    active = fields.Boolean('Hoạt động', default=True)

    state = fields.Selection(
        [('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'), ('refuse', 'Từ chối'), ('cancel', 'Hủy')],
        'Trạng thái', default='draft', tracking=True)

    trp_approve_history_ids = fields.One2many('trp.approve.history', 'details_internal_tf_book_id', string='Lịch sử duyệt', copy=False)

    def unlink(self):
        for record in self:
            if record.state not in ['refuse', 'cancel', 'draft']:
                raise UserError("Không thể xóa yêu cầu ký đã duyệt!")
        return super(DetailsInternalTfBook, self).unlink()

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
        res = super(DetailsInternalTfBook, self).action_agree()
        for record in self:
            if record.state == 'approved':
                record.director_id = self.env.user.id
                try:
                    report_pdf = self.env['ir.actions.report']._render_qweb_pdf(
                        'biz_details_purchase_report.action_details_internal_tf_book_pdf', record.id)
                    record.message_post(
                        body=f"Sổ chi tiết nhập hàng tại cảng {record._get_html_link()}",
                        attachments=[(f'{record.name}.pdf', report_pdf[0])],
                    )
                except Exception:
                    record.message_post(
                        body=f"Sổ chi tiết nhập hàng tại cảng {record._get_html_link()} đã được duyệt.",
                    )
        return res

    def action_print_excel(self):
        return self.env.ref('biz_details_purchase_report.action_details_internal_tf_book_xlsx').report_action(self)

    def action_print_pdf(self):
        return self.env.ref('biz_details_purchase_report.action_details_internal_tf_book_pdf').report_action(self)

    @api.model
    def default_get(self, fields_list):
        defaults = super(DetailsInternalTfBook, self).default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()
        chief_finance_id = env_params.get_param('biz_details_purchase_report.tf_book_chief_finance_id', False)
        accounting_department_id = env_params.get_param('biz_details_purchase_report.tf_book_accounting_department_id', False)
        director_id = env_params.get_param('biz_details_purchase_report.director_id', False)
        date_from = date.today().strftime('%d%m%Y')
        date_to = date.today().strftime('%d%m%Y')
        defaults.update({
            'voter_id': self.env.user.id,
            'chief_finance_id': int(chief_finance_id) if chief_finance_id and chief_finance_id != '0' else False,
            'accounting_department_id': int(accounting_department_id) if accounting_department_id and accounting_department_id != '0' else False,
            'director_id': int(director_id) if director_id and director_id != '0' else False,
            'name': f'Nhập hàng tại cảng {date_from} - {date_to}',
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
                    name = f'Nhập hàng tại cảng ngày {date_from}'
                else:
                    name = f'Nhập hàng tại cảng {date_from} - {date_to}'
                if warehouse_names:
                    name += f' - {warehouse_names}'
                record.name = name

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError("'Đến ngày' phải lớn hơn hoặc bằng 'Từ ngày'.")

    def action_confirm(self):
        """Lấy dữ liệu từ stock.move tương tự logic RpInternalTfWizardReport._get_data_export"""
        self = self.with_context(tz=self.env.user.tz).sudo()
        self.ensure_one()
        self.line_ids.unlink()

        start_datetime = datetime.combine(self.date_from, datetime.min.time()) - timedelta(hours=7)
        end_datetime = datetime.combine(self.date_to, datetime.max.time()) - timedelta(hours=7)

        warehouse_ids = self.warehouse_ids if self.warehouse_ids else self.env['stock.warehouse'].search([])
        line_vals = []

        for warehouse_id in warehouse_ids:
            sms = self.env['stock.move'].search([
                ('picking_id', '!=', False),
                ('picking_id.stock_date_receipt', '>=', start_datetime),
                ('picking_id.stock_date_receipt', '<=', end_datetime),
                '|',
                ('location_id.warehouse_id', '=', warehouse_id.id),
                ('location_dest_id.warehouse_id', '=', warehouse_id.id),
                ('state', '=', 'done'),
                '|',
                ('picking_id.purchase_id', '!=', False),
                ('picking_id.purchase_order_id', '!=', False),
            ], order='date asc')

            for sm in sms:
                order_info = self._get_order_info(warehouse_id, sm)
                if not order_info or order_info.get('order', '') == '':
                    continue
                if order_info.get('quantity', 0) == 0:
                    continue

                line_vals.append({
                    'parent_id': self.id,
                    'date': (sm.date + timedelta(hours=7)).date() if sm.date else False,
                    'name': sm.reference or '',
                    'partner_name': sm.partner_id.name if sm.partner_id else '',
                    'product_code': sm.product_id.default_code or '',
                    'product_name': sm.product_id.name or '',
                    'uom_name': sm.product_uom.name or '',
                    'warehouse_code': warehouse_id.code or '',
                    'account': sm.account_id.code if sm.account_id else '',
                    'account_ctp': ','.join(sm.account_dest_ids.mapped('code')) if sm.account_dest_ids else '',
                    'exchange_rate': order_info.get('exchange_rate', 0),
                    'price_unit': order_info.get('price_unit', 0),
                    'price_unit_w_currency': order_info.get('price_unit_w_currency', 0),
                    'amount_total': order_info.get('amount_total', 0),
                    'amount_total_w_currency': order_info.get('amount_total_w_currency', 0),
                    'quantity': order_info.get('quantity', 0),
                    'return_quantity': order_info.get('return_quantity', 0),
                    'amount_total_return': order_info.get('amount_total_return', 0),
                    'amount_total_return_w_currency': order_info.get('amount_total_return_w_currency', 0),
                    'order_name': order_info.get('order', ''),
                    'partner_name': order_info.get('partner_name', sm.partner_id.name if sm.partner_id else ''),
                })

        if line_vals:
            self.env['details.internal.tf.book.line'].create(line_vals)

    def _get_order_info(self, warehouse_id, sm):
        """Tái sử dụng logic từ ccv_bao_cao.RpInternalTfWizardReport._get_order_info"""
        import re
        from bs4 import BeautifulSoup

        def html_to_text(html_content):
            if not html_content:
                return ''
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text(separator='\n').strip()

        if not sm or not sm.picking_id:
            return None

        is_return = warehouse_id.id == sm.location_id.warehouse_id.id
        reason_output_input_stock = sm.picking_id.reason_output_input_stock
        origin = sm.picking_id.origin
        purchase_order = None

        if not is_return:
            quantity = sm.quantity_done
            return_quantity = 0
        else:
            quantity = 0
            return_quantity = sm.quantity_done

        if origin and origin.startswith('PO'):
            purchase_order = self.env['purchase.order'].search([('name', '=', origin)], limit=1)

        if not purchase_order:
            if reason_output_input_stock:
                reason_text = html_to_text(reason_output_input_stock)
                stk_match = re.search(r'STK\s*[:]?\s*(\d+)', reason_text)
                if stk_match:
                    customs_declaration_number = stk_match.group(1)
                    am = self.env['account.move'].search([('ref', 'ilike', customs_declaration_number)])
                    invl = am.invoice_line_ids.filtered(lambda l: l.product_id == sm.product_id)
                    if invl and invl.purchase_line_id:
                        purchase_order = invl.purchase_line_id.order_id
                    else:
                        pk = self.env['stock.picking'].search([
                            ('purchase_id', '!=', False),
                            ('reason_output_input_stock', 'ilike', customs_declaration_number)
                        ])
                        if pk:
                            purchase_order = pk[0].purchase_id

        val = {
            'exchange_rate': 0,
            'price_unit': 0,
            'amount_total': 0,
            'amount_total_return': 0,
            'price_unit_w_currency': 0,
            'amount_total_w_currency': 0,
            'amount_total_return_w_currency': 0,
            'order': '',
            'quantity': quantity,
            'return_quantity': return_quantity,
        }

        if purchase_order:
            purchase_order = purchase_order[0]
            exchange_rate = purchase_order.inverse_manural_currency_exchange_rate if purchase_order.apply_manual_currency_exchange else 0
            order_line = purchase_order.order_line.filtered(lambda l: l.product_id == sm.product_id)
            if order_line:
                order_line = order_line[0]
                price_unit = order_line.price_unit
                price_unit_w = price_unit * exchange_rate if purchase_order.apply_manual_currency_exchange else price_unit
                price_unit_w_currency = price_unit if purchase_order.apply_manual_currency_exchange else 0

                amount_total = amount_total_w_currency = amount_total_return = amount_total_return_w_currency = 0
                if not is_return:
                    amount_total = price_unit_w * quantity
                    amount_total_w_currency = price_unit_w_currency * quantity if purchase_order.apply_manual_currency_exchange else 0
                else:
                    amount_total_return = price_unit_w * return_quantity
                    amount_total_return_w_currency = price_unit_w_currency * return_quantity if purchase_order.apply_manual_currency_exchange else 0

                val.update({
                    'exchange_rate': exchange_rate,
                    'price_unit': price_unit_w,
                    'amount_total': amount_total,
                    'amount_total_return': amount_total_return,
                    'price_unit_w_currency': price_unit_w_currency,
                    'amount_total_w_currency': amount_total_w_currency,
                    'amount_total_return_w_currency': amount_total_return_w_currency,
                    'order': purchase_order.name,
                    'partner_name': purchase_order.partner_id.name,
                })
        return val
