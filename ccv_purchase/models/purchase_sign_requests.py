# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class PurchaseSignRequests(models.Model):
    _name = 'purchase.sign.requests'
    _inherit = ['sign.requests']
    _description = 'Purchase Sign Requests'

    # Override name field để related với purchase_order_id
    name = fields.Char(string="Tên", required=True, copy=False, readonly=True, related='purchase_order_id.name')
    
    # Field specific cho purchase
    purchase_order_id = fields.Many2one('purchase.order', string="Đơn mua hàng", required=True, ondelete='cascade')
    
    # Override partner_id để related với purchase_order_id
    partner_id = fields.Many2one("res.partner", string="Nhà cung cấp", related="purchase_order_id.partner_id", store=True)
    
    # Override trp_approve_history_ids để sử dụng đúng field
    trp_approve_history_ids = fields.One2many('trp.approve.history', 'purchase_sign_requests_id', string='Lịch sử duyệt', copy=False)
    
    # Sử dụng order_line trực tiếp từ purchase.order
    order_line = fields.One2many('purchase.order.line', 'order_id', related='purchase_order_id.order_line', string='Chi tiết đơn mua hàng')
    
    # Purchase sign requests lines
    purchase_sign_requests_line_ids = fields.One2many('purchase.sign.requests.line', 'sign_requests_id', string='Chi tiết yêu cầu ký', readonly=True)
    
    # Override các field tiền tệ để related với purchase_order_id
    amount_untax_total = fields.Monetary("Tổng chưa thuế")
    amount_tax_total = fields.Monetary("Tổng thuế")
    amount_total = fields.Monetary("Tổng cộng")
    currency_id = fields.Many2one('res.currency', string='Tiền tệ')
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)

    date_planned = fields.Date(string='Ngày giao hàng')
    date_approve = fields.Date(string='Ngày ký')
    debit = fields.Monetary("Số dư nợ")
    description = fields.Text(string='Diễn giải')


    @api.depends_context('lang')
    @api.depends('purchase_order_id.tax_totals')
    def _compute_tax_totals(self):
        for record in self:
            record.tax_totals = record.purchase_order_id.tax_totals

    def _create_sign_requests_lines(self):
        """Tạo purchase_sign_requests_line từ purchase_order_line"""
        for record in self:
            if record.purchase_order_id and record.purchase_order_id.order_line:
                # Xóa các line cũ nếu có
                record.purchase_sign_requests_line_ids.unlink()
                
                # Tạo line mới từ purchase_order_line
                for order_line in record.purchase_order_id.order_line.filtered(lambda l: not l.display_type and l.product_qty > 0):
                    # Tạo line với purchase_order_line_id
                    self.env['purchase.sign.requests.line'].create({
                        'sign_requests_id': record.id,
                        'purchase_order_line_id': order_line.id,
                        'name': order_line.name,
                        'product_image': order_line.product_id.image_1920,
                        'product_id': order_line.product_id.id if order_line.product_id else False,
                        'product_uom_qty': order_line.product_qty,
                        'product_uom': order_line.product_uom.id if order_line.product_uom else False,
                        'price_unit': order_line.price_unit,
                        'tax_id': [(6, 0, order_line.taxes_id.ids)],
                        'currency_id': order_line.currency_id.id if order_line.currency_id else False,
                        'amount_untax': order_line.price_subtotal,
                        'amount_tax': order_line.price_tax,
                        'amount_total': order_line.price_total,
                    })

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        for record in self:
            if record.purchase_order_id:
                record._create_sign_requests_lines()

    @api.constrains('purchase_order_id', 'state')
    def _check_one_active_request(self):
        for record in self:
            if record.state != 'cancel':
                # Kiểm tra xem có yêu cầu ký nào khác đang thực hiện không
                active_requests = self.env['purchase.sign.requests'].search([
                    ('purchase_order_id', '=', record.purchase_order_id.id),
                    ('id', '!=', record.id),
                    ('state', 'not in', ['cancel'])
                ])
                if active_requests:
                    raise ValidationError('Đơn mua hàng này đã có yêu cầu ký đang thực hiện. Chỉ được tạo yêu cầu mới khi yêu cầu hiện tại đã hủy.')

    def action_view_purchase_order(self):
        return {
            'name': 'Đơn mua hàng',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'res_id': self.purchase_order_id.id,
            'context': {
                'create': False,
                'edit': False,
            }
        }
    
    def action_agree(self):
        res = super(PurchaseSignRequests, self).action_agree()
        for record in self:
            if record.state == 'approved':
                # Sử dụng py3o report
                report_action = self.env.ref("ccv_bao_cao.action_report_purchaseorder_new_2025_pdf")
                report_pdf = report_action._render_py3o(report_action.report_name, record.purchase_order_id.ids, {})
                record.message_post(
                    body=f"Phiếu ký đơn mua hàng {record._get_html_link()}",
                    attachments=[(f'{record.name}.pdf', report_pdf[0])],
                )
                record.purchase_order_id.message_post(
                    body=f"Phiếu ký đơn mua hàng {record._get_html_link()}",
                    attachments=[(f'{record.name}.pdf', report_pdf[0])],
                )
        return res
