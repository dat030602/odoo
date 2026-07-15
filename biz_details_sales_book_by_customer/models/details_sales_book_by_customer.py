# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta
import re
import html2text
from bs4 import BeautifulSoup
import logging

_logger = logging.getLogger(__name__)

class DetailsSalesBookByCustomer(models.Model):
    _name = 'details.sales.book.by.customer'
    _description = 'Sổ chi tiết bán hàng theo khách hàng' 
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']

    name = fields.Char('Tên')
    date_from = fields.Date('Từ ngày', default=date.today())
    date_to = fields.Date('Đến ngày', default=date.today())
    creator_id = fields.Many2one('res.users', string='Người lập biểu')
    statistics_id = fields.Many2one('res.users', string='Thống kê BĐH')
    account_liability_id = fields.Many2one('res.users', string='Phòng kế toán')
    accountant_chief_id = fields.Many2one('res.users', string='Kế toán trưởng')
    unit_head_id = fields.Many2one('res.users', string='Thủ trưởng đơn vị')
    line_ids = fields.One2many('details.sales.book.by.customer.line', 'parent_id', string='Chi tiết')
    active = fields.Boolean('Hoạt động', default=True)

    # Bộ lọc
    type_partner = fields.Selection([('1', 'Một khách hàng'), ('team', 'Khu vực'), ('order_state', 'Tỉnh/Thành phố'), ('all', 'Tất cả')], string='Loại khách hàng',default='all')
    partner_id = fields.Many2one('res.partner', string='Khách hàng')
    team_id = fields.Many2many('crm.team', string='Khu vực')
    order_state_id = fields.Many2one('res.country.state', string='Tỉnh/Thành phố')

    state = fields.Selection(
        [('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'), ('refuse', 'Từ chối'), ('cancel', 'Hủy')], 
        'Trạng thái', default="draft", tracking=True)
    
    trp_approve_history_ids = fields.One2many('trp.approve.history', 'dsk_customer_id', string='Lịch sử duyệt', copy=False)

    def unlink(self):
        for record in self:
            if record.state not in ['refuse', 'cancel','draft']:
                raise UserError("Không thể xóa yêu cầu ký đã duyệt!")
        return super(DetailsSalesBookByCustomer, self).unlink()

    def action_cancel(self):
        self.write({
            'state': 'cancel'
        })
        res_history = self.trp_approve_history_ids
        self.env['mail.activity'].search([('trp_approve_history_id', 'in', res_history.ids)]).with_context(skip_approve_done=True).action_done()

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
                self.update({
                    'state': 'approved',
                })
                return

    def action_undo(self):
        self.write({
            'state': 'draft'
        })

    def action_agree(self):
        res = super(DetailsSalesBookByCustomer, self).action_agree()
        for record in self:
            if record.state == 'approved':
                report_pdf = self.env['ir.actions.report']._render_qweb_pdf("biz_details_sales_book_by_customer.action_details_sales_book_by_customer_pdf", record.id)
                record.message_post(
                    body=f"Sổ chi tiết bán hàng theo khách hàng {record._get_html_link()}",
                    attachments=[(f'{record.name}.pdf', report_pdf[0])],
                )
        return res

    @api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.manager_type',
                 'trp_approve_config_line_id.user_ids', \
                 'trp_approve_config_line_id.job_ids')
    def _compute_current_approve_users(self):
        super(DetailsSalesBookByCustomer, self)._compute_current_approve_users()
        user = self.env.user.sale_team_id.user_id
        for record in self:
            list_approver = []
            current_approve_user_ids = record.current_approve_user_ids
            if record.trp_approve_config_line_id and record.trp_approve_config_line_id.manager_type and record.trp_approve_config_line_id.manager_type == "parent" and user:
                user_parent = user.id
                if user_parent:
                    list_approver.append(user_parent)
                record.current_approve_user_ids = [(6, 0, list_approver)]
            else:
                record.current_approve_user_ids = [(6, 0, current_approve_user_ids.ids)]


    @api.onchange("type_partner","partner_id","team_id","order_state_id", "date_from", "date_to")
    def _onchange_type_partner(self):
        for rec in self.sudo():
            prefix = "Sổ chi tiết bán hàng theo khách hàng - "
            date_str = f'{rec.date_from.strftime("%d%m%Y") if rec.date_from else ""} - {rec.date_to.strftime("%d%m%Y") if rec.date_to else ""}'
            if rec.type_partner == 'team':
                if not rec.team_id:
                    rec.team_id = self.env['crm.team'].search([
                        '|', '|',
                        ('user_id','=',rec.env.user.id),
                        ('member_ids','in',[rec.env.user.id]),
                        ('sales_assistant_ids','in',[rec.env.user.id]),
                    ], limit=1)
                if rec.team_id:
                    team_names = ', '.join(rec.team_id.mapped(lambda t: t.report_name or t.name or ''))
                    rec.name = f'{prefix}{team_names} - {date_str}'
            elif rec.type_partner == 'order_state' and rec.order_state_id:
                rec.name = f'{prefix}{rec.order_state_id.name} - {date_str}'
            elif rec.type_partner == '1' and rec.partner_id:
                rec.name = f'{prefix}{rec.partner_id.name} - {date_str}'
            else:
                rec.name = f'{prefix}{date_str}'

    @api.model
    def default_get(self, fields_list):
        defaults = super(DetailsSalesBookByCustomer, self).default_get(fields_list)

        env_params = self.env['ir.config_parameter'].sudo()
        chief_finance_id = env_params.get_param('biz_details_sales_book_by_customer.chief_accountant_id', False)
        director_id = env_params.get_param('biz_details_sales_book_by_customer.director_id', False)
        statistics_id = env_params.get_param('biz_details_sales_book_by_customer.statistics_id', False)
        account_liability_id = env_params.get_param('biz_details_sales_book_by_customer.account_liability_id', False)
        date_from = date.today().strftime("%d%m%Y")
        date_to = date.today().strftime("%d%m%Y")
        
        defaults.update({
            'creator_id': self.env.user.id,
            'statistics_id': int(statistics_id) if statistics_id else False,
            'account_liability_id': int(account_liability_id) if account_liability_id else False,
            'accountant_chief_id': int(chief_finance_id) if chief_finance_id else False,
            'unit_head_id': int(director_id) if director_id else False,
            'name': f'Sổ chi tiết bán hàng theo khách hàng - {date_from} - {date_to}',
        })
        return defaults

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError("'Đến ngày' phải lớn hơn hoặc bằng 'Từ ngày'.")
    
    def action_print_pdf(self):
        return self.env.ref('biz_details_sales_book_by_customer.action_details_sales_book_by_customer_pdf').report_action(self)
    
    def action_print_excel(self):
        return self.env.ref('biz_details_sales_book_by_customer.action_details_sales_book_by_customer_xlsx').report_action(self)

    def action_confirm(self):
        self = self.with_context(tz=self.env.user.tz).sudo()
        self.ensure_one()
        self.line_ids.unlink()
        # date_from: minimal time of date_from (00:00:00), date_to: maximum time of date_to (23:59:59.999999)
        date_from = datetime.combine(self.date_from, datetime.min.time()) - timedelta(hours=7)
        date_to = datetime.combine(self.date_to, datetime.max.time()) - timedelta(hours=7)
        
        # Get stock moves with same logic as get_lines
        StockMove = self.env['stock.move'].with_context(tz=self.env.user.tz).sudo()
        domain = [('sale_line_id', '!=', False), ('location_dest_id.usage', '=', 'customer'), ('state', '=', 'done')]
        if self.date_from:
            domain.append(('picking_id.stock_date_receipt','>=', date_from))
        if self.date_to:
            domain.append(('picking_id.stock_date_receipt','<=', date_to))
        if self.type_partner == '1':
            domain.append(('picking_id.partner_id', '=', self.partner_id.id))
        elif self.type_partner == 'team':
            domain.append(('picking_id.partner_id.team_id', 'in', self.team_id.ids))
        elif self.type_partner == 'order_state':
            domain.append(('picking_id.partner_id.state_id', '=', self.order_state_id.id))
        
        StockMoves = StockMove.search(domain).sorted(key=lambda m: (
            m.date.date() if m.date else datetime.min.date(),
            m.picking_id.write_date,
            m.picking_id.partner_id.id if m.picking_id.partner_id else 0,
        ))
        
        line_vals = []
        for line in StockMoves:
            qty_done = 0.000
            move_dest_ids = line.move_dest_ids.filtered(lambda x: x.state == 'done')
            if move_dest_ids:
                qty_done = sum(move_dest_ids.mapped('quantity_done'))
            quantity_done = (line.quantity_done - qty_done) if move_dest_ids.filtered(lambda x: not x.picking_id.is_actual_return_with_invoice) else line.quantity_done
            qty_done = 0.000
            if move_dest_ids.filtered(lambda x: x.picking_id.is_actual_return_with_invoice):
                qty_done = sum(move_dest_ids.mapped('quantity_done'))
                
            price_unit = float(line.sale_line_id.price_unit) if line.sale_line_id and line.sale_line_id.price_unit else 0.000
            
            invoice_lines = line.sale_line_id.invoice_lines.filtered(lambda x: x.move_id) if line.sale_line_id else self.env['account.move.line'].sudo()
            vat_sinvoice_numbers = []
            vat_sinvoice_dates = []
            if invoice_lines:
                moves = invoice_lines.mapped('move_id')
                vat_sinvoice_numbers = [m.vat_sinvoice_number for m in moves if m.vat_sinvoice_number]
                vat_sinvoice_dates = [m.invoice_date for m in moves if m.invoice_date]
            
            vat_sinvoice_number = ', '.join(list(set(vat_sinvoice_numbers))) if vat_sinvoice_numbers else ''
            vat_sinvoice_date = vat_sinvoice_dates[0] if vat_sinvoice_dates else False
            
            date_value = False
            if line.picking_id and line.picking_id.stock_date_receipt:
                date_vn = line.picking_id.stock_date_receipt + timedelta(hours=7)
                date_value = date_vn.date()
                
            if line.product_uom != line.sale_line_id.product_uom:
                quantity_done = line.product_uom._compute_quantity(quantity_done, line.sale_line_id.product_uom) if line.sale_line_id else quantity_done
                qty_done = line.product_uom._compute_quantity(qty_done, line.sale_line_id.product_uom) if line.sale_line_id else qty_done
            
            taxes = line.sale_line_id.tax_id.sudo().compute_all(price_unit, line.sale_line_id.currency_id, quantity_done, product=line.product_id)
            price_subtotal = taxes['total_excluded'] or 0.000
            amount_tax = taxes['total_included'] - taxes['total_excluded'] or 0.000
            price_subtotal_tax = taxes['total_included'] or 0.000

            vehicle_info_parts = []
            if line.picking_id and line.picking_id.vehicle_license_plate:
                vehicle_info_parts.append(line.picking_id.vehicle_license_plate)
            if line.picking_id and line.picking_id.vehicle_driver_name:
                vehicle_info_parts.append(line.picking_id.vehicle_driver_name)

            if vehicle_info_parts:
                stock_sale_export = " - ".join(vehicle_info_parts)
            else:
                stock_sale_export = line.picking_id and self._get_reason_output_input_stock(line.picking_id.reason_output_input_stock) or ''
            
            line_vals.append({
                'parent_id': self.id,
                'reference': line.reference or '',
                'date': date_value,
                'vat_sinvoice_number': vat_sinvoice_number,
                'vat_sinvoice_date': vat_sinvoice_date,
                'picking_id': line.picking_id.id if line.picking_id else False,
                'stock_sale_export': stock_sale_export,
                'partner_id': line.partner_id.id if line.partner_id else False,
                'product_id': line.product_id.id if line.product_id else False,
                'qty_invoiced': quantity_done,
                'price_unit': price_unit,
                'price_subtotal': price_subtotal,
                'amount_tax': amount_tax,
                'price_subtotal_tax': price_subtotal_tax,
                'qty_done': qty_done,
                'price_done': price_unit * qty_done if price_unit and qty_done else 0.000,
                'sale_line_id': line.sale_line_id.id if line.sale_line_id else False,
            })
        
        if line_vals:
            self.env['details.sales.book.by.customer.line'].create(line_vals)
    
    def _get_reason_output_input_stock(self, reason_output_input_stock):
        """Helper method to process HTML content from reason_output_input_stock field"""
        if reason_output_input_stock:
            soup = BeautifulSoup(reason_output_input_stock, 'lxml')
            soup_format = soup.prettify()
            html2_text = html2text.html2text(soup_format)
            clean_note = re.sub(r'[^\w\s,\-]', '', html2_text)
            clean_note = '\n'.join([line.strip() for line in clean_note.splitlines() if line.strip()])
            return clean_note.strip()
        return ''

    def action_view_details(self):
        self.ensure_one()
        action = self.env.ref('biz_details_sales_book_by_customer.action_details_sales_book_by_customer_line').sudo().read()[0]
        action['domain'] = [('parent_id', '=', self.id)]
        return action
