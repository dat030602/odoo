# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class SaleSignRequests(models.Model):
    _name = 'sale.sign.requests'
    _inherit = ['sign.requests']
    _description = 'Sale Sign Requests'

    # Override name field để related với sale_order_id
    name = fields.Char(string="Tên", required=True, copy=False, readonly=True, related='sale_order_id.name')
    
    # Field specific cho sale
    sale_order_id = fields.Many2one('sale.order', string="Đơn hàng", required=True, ondelete='cascade')
    
    # Override partner_id để related với sale_order_id
    partner_id = fields.Many2one("res.partner", string="Khách hàng", related="sale_order_id.partner_id", store=True)
    
    # Override trp_approve_history_ids để sử dụng đúng field
    trp_approve_history_ids = fields.One2many('trp.approve.history', 'sale_sign_requests_id', string='Lịch sử duyệt', copy=False)
    
    # Sử dụng order_line trực tiếp từ sale.order
    order_line = fields.One2many('sale.order.line', 'order_id', related='sale_order_id.order_line', string='Chi tiết đơn hàng')
    
    # Sale sign requests lines
    sale_sign_requests_line_ids = fields.One2many('sale.sign.requests.line', 'sign_requests_id', string='Chi tiết yêu cầu ký', readonly=True)
    
    # Override các field tiền tệ để related với sale_order_id
    amount_untax_total = fields.Monetary("Tổng chưa thuế")
    amount_tax_total = fields.Monetary("Tổng thuế")
    amount_total = fields.Monetary("Tổng cộng")
    currency_id = fields.Many2one('res.currency', string='Tiền tệ')
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)

    contact_total_due = fields.Monetary("Tổng cộng nợ")
    credit_limit = fields.Monetary("Hạn mức công nợ")
    contact_phone = fields.Char("Số điện thoại")
    contact_representative = fields.Char("Người đại diện")
    payment_term_id = fields.Many2one('account.payment.term', string='Điều kiện thanh toán')
    payment_type = fields.Selection([('cash', 'Tiền mặt'), ('bank', 'Chuyển khoản')], string='Loại thanh toán')
    internal_note = fields.Text("Ghi chú")
    user_id = fields.Many2one('res.users', string='Nhân viên kinh doanh')
    team_id = fields.Many2one('crm.team', string='Đội bán hàng')
    origin = fields.Char("Nguồn")
    commitment_date = fields.Datetime(related='sale_order_id.commitment_date', string='Ngày cam kết giao hàng', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', related='sale_order_id.pricelist_id', string='Bảng giá', readonly=True)
    bonus_price_id = fields.Many2one(related='sale_order_id.bonus_price_id', string='Quỹ dự phòng', readonly=True)
    promotion_ccv_id = fields.Many2one(related='sale_order_id.promotion_ccv_id', string='Khuyến mãi', readonly=True)
    sales_team_captain_id = fields.Many2one('res.users', string='Trưởng đội bán hàng')

    @api.depends_context('lang')
    @api.depends('order_line.tax_id', 'order_line.price_subtotal', 'amount_total', 'amount_untax_total')
    def _compute_tax_totals(self):
        for record in self:
            order_lines = record.order_line.filtered(lambda x: not x.display_type)
            record.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                record.currency_id or record.company_id.currency_id,
            )

    def _create_sign_requests_lines(self):
        """Tạo sale_sign_requests_line từ sale_order_line"""
        for record in self:
            if record.sale_order_id and record.sale_order_id.order_line:
                # Xóa các line cũ nếu có
                record.sale_sign_requests_line_ids.unlink()
                
                # Tạo line mới từ sale_order_line
                for order_line in record.sale_order_id.order_line.filtered(lambda l: not l.display_type and l.product_uom_qty > 0):
                    # Tạo line với sale_order_line_id
                    self.env['sale.sign.requests.line'].create({
                        'sign_requests_id': record.id,
                        'sale_order_line_id': order_line.id,
                        'name': order_line.name,
                        'packaging_image': order_line.packaging_image,
                        'product_image': order_line.product_image,
                        'product_id': order_line.product_id.id if order_line.product_id else False,
                        'product_uom_qty': order_line.product_uom_qty,
                        'product_uom': order_line.product_uom.id if order_line.product_uom else False,
                        'price_unit': order_line.price_unit,
                        'tax_id': [(6, 0, order_line.tax_id.ids)],
                        'currency_id': order_line.currency_id.id if order_line.currency_id else False,
                        'amount_untax': order_line.price_total,
                        'amount_tax': order_line.price_tax,
                        'amount_total': order_line.price_subtotal,
                    })

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        for record in self:
            if record.sale_order_id:
                record._create_sign_requests_lines()

    @api.constrains('sale_order_id', 'state')
    def _check_one_active_request(self):
        for record in self:
            if record.state != 'cancel':
                # Kiểm tra xem có yêu cầu ký nào khác đang thực hiện không
                active_requests = self.env['sale.sign.requests'].search([
                    ('sale_order_id', '=', record.sale_order_id.id),
                    ('id', '!=', record.id),
                    ('state', 'not in', ['cancel'])
                ])
                if active_requests:
                    raise ValidationError('Đơn hàng này đã có yêu cầu ký đang thực hiện. Chỉ được tạo yêu cầu mới khi yêu cầu hiện tại đã hủy.')

    def action_view_sale_order(self):
        return {
            'name': 'Đơn hàng',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'res_id': self.sale_order_id.id,
            'context': {
                'create': False,
                'edit': False,
            }
        }

    def action_agree(self):
        to_check_sale_request = 'KD' not in self.sale_order_id.sale_order_type_id.code
        res = super(SaleSignRequests, self.with_context(to_check_sale_request=to_check_sale_request)).action_agree()
        for record in self:
            if record.state == 'approved':
                # Sử dụng py3o report
                report_action = self.env.ref("ccv_bao_cao.action_report_saleorder_new_2025_pdf")
                report_pdf = report_action._render_py3o(report_action.report_name, record.sale_order_id.ids, {})
                record.message_post(
                    body=f"Phiếu ký đơn hàng {record._get_html_link()}",
                    attachments=[(f'{record.name}.pdf', report_pdf[0])],
                )
                record.sale_order_id.message_post(
                    body=f"Phiếu ký đơn hàng {record._get_html_link()}",
                    attachments=[(f'{record.name}.pdf', report_pdf[0])],
                )
        return res

    @api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.manager_type',
                 'trp_approve_config_line_id.user_ids', \
                 'trp_approve_config_line_id.job_ids')
    def _compute_current_approve_users(self):
        super(SaleSignRequests, self)._compute_current_approve_users()
        for record in self:
            list_approver = []
            current_approve_user_ids = record.current_approve_user_ids
            if record.trp_approve_config_line_id and record.trp_approve_config_line_id.manager_type and record.trp_approve_config_line_id.manager_type == "parent" and record.sales_team_captain_id:
                user_parent = record.sales_team_captain_id.id
                if user_parent:
                    list_approver.append(user_parent)
                record.current_approve_user_ids = [(6, 0, list_approver)]
            else:
                record.current_approve_user_ids = [(6, 0, current_approve_user_ids.ids)]


    def action_confirm(self):
        res = super(SaleSignRequests, self).action_confirm()
        self = self.sudo()
        products = self.sale_sign_requests_line_ids.mapped('product_id')
        for product in products:
            lines = self.sale_sign_requests_line_ids.filtered(lambda l: l.product_id == product)
            product.qty_ordered = product.qty_ordered + sum(lines.mapped('product_uom_qty'))
            product.qty_order_delivered = product.qty_order_delivered + sum(lines.mapped('sale_order_line_id.qty_delivered'))
        return res
