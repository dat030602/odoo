from odoo import fields, models, api, _
from odoo.exceptions import UserError
import datetime
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    can_finalize_shipment = fields.Boolean(compute="_compute_can_finalize_shipment")
    chief_accountant_id = fields.Many2one('res.users', string='Kế toán trưởng')
    unit_head_id = fields.Many2one('res.users', string='Thủ trưởng đơn vị')
    approval_request_ids = fields.Many2many(
        'approval.request',
        'purchase_order_approval_request_rel',
        'purchase_order_id',
        'approval_request_id',
        string='Mã đề xuất',
    )

    @api.onchange('origin')
    def _onchange_origin_approval_request(self):
        for order in self:
            if not order.origin:
                order.approval_request_ids = [(5, 0, 0)]
                continue
            matched = self.env['approval.request']
            matched |= self.env['approval.request'].sudo().search([('name', '=', order.origin)])
            matched |= self.env['approval.request'].sudo().search([('name', 'ilike', order.origin)])
            for part in order.origin.split('/'):
                part = part.strip()
                if part:
                    matched |= self.env['approval.request'].sudo().search([('name', 'ilike', part)])
            if not matched:
                all_reqs = self.env['approval.request'].sudo().search(
                    [('name', '!=', False)], order='id desc', limit=500
                )
                for req in all_reqs:
                    if req.name in order.origin:
                        matched |= req
                    elif '/' in req.name:
                        suffix = req.name.split('/')[1]
                        if suffix and suffix in order.origin:
                            matched |= req
            order.approval_request_ids = [(6, 0, matched.ids)]

    @api.onchange('apply_manual_currency_exchange','inverse_manural_currency_exchange_rate')
    def _onchange_apply_manual_currency_exchange(self):
        for rec in self:
            if rec.apply_manual_currency_exchange:
                rec.order_line._origin.recompute_exchange_rate_svl(rec.inverse_manural_currency_exchange_rate)
    
    @api.depends('currency_id','order_line.qty_invoiced','order_line.qty_received')
    def _compute_can_finalize_shipment(self):
        for rec in self:
            qty_invoiced = sum(rec.order_line.mapped('qty_invoiced'))
            qty_received = sum(rec.order_line.mapped('qty_received'))
            if rec.currency_id.name != 'VND' and (qty_invoiced != 0) and (qty_received != 0):
                can_finalize_shipment = True
            else:
                can_finalize_shipment = False
            rec.can_finalize_shipment = can_finalize_shipment
    
    @api.depends_context('lang')
    @api.depends('order_line.taxes_id', 'order_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals(self):
        res = super(PurchaseOrder,self)._compute_tax_totals()
        for order in self.with_context(lang='vi_VN'):
            tax_totals = order.tax_totals or {}
            tax_totals.update({
                'amount_untaxed': order.amount_untaxed,
                'formatted_amount_untaxed': order.currency_id.format(order.amount_untaxed),
                'amount_total': order.amount_total,
                'formatted_amount_total': order.currency_id.format(order.amount_total),
            })
            tax_totals.update({
                'subtotals': {
                    'amount_untaxed': order.amount_untaxed,
                    'formatted_amount_untaxed': order.currency_id.format(order.amount_untaxed),
                },
            })
            untaxes = tax_totals.get('groups_by_subtotal', {}).get('Tổng chưa thuế', [])
            for untax in untaxes:
                orderline = order.order_line.filtered(lambda x: untax.get('tax_group_id') in x.taxes_id.mapped('tax_group_id.id'))
                sum_price_tax = sum(orderline.mapped('price_tax'))
                sum_price_subtotal = sum(orderline.mapped('price_subtotal'))
                untax.update({
                    "tax_group_amount": sum_price_tax,
                    "tax_group_base_amount": sum_price_subtotal,
                    "formatted_tax_group_amount": order.currency_id.format(sum_price_tax),
                    "formatted_tax_group_base_amount": order.currency_id.format(sum_price_subtotal),
                })
            order.tax_totals = tax_totals
        return res
    
    def action_stock_move_wizard(self):
        self.ensure_one()
        action = self.env.ref('ccv_purchase.action_stock_move_wizard').sudo().read()[0]
        action['context'] = {
            'purchase_order_id': self.id,
        }
        return action

    @api.depends('order_line.invoice_lines.move_id','order_line.move_ids.account_move_ids')
    def _compute_invoice(self):
        res = super(PurchaseOrder,self)._compute_invoice()
        for order in self:
            order.invoice_ids |= order.order_line.move_ids.mapped('account_move_ids')
            order.invoice_count = len(order.invoice_ids)
        return res

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        res.update({
            'invoice_date': datetime.date.today(),
            'document_date': datetime.date.today(),
            'report_date': datetime.date.today(),
            'ref': self.custom_declaration_number or '',
            'note': self.description or '',
        })
        return res

    # Purchase Sign Requests
    purchase_sign_requests_ids = fields.One2many('purchase.sign.requests', 'purchase_order_id', string='Yêu cầu ký')
    purchase_sign_requests_id = fields.Many2one('purchase.sign.requests', 'Yêu cầu ký', compute='_compute_purchase_sign_requests_id')
    purchase_sign_requests_history_ids = fields.Many2many('trp.approve.history', 'purchase_sign_requests_history_ids', string='Lịch sử duyệt', compute='_compute_purchase_sign_requests_history_ids')
    purchase_sign_requests_count = fields.Integer(string='Số yêu cầu ký', compute='_compute_purchase_sign_requests_count')
    purchase_sign_requests_state = fields.Selection('Trạng thái duyệt', related='purchase_sign_requests_id.state')

    @api.depends('purchase_sign_requests_ids')
    def _compute_purchase_sign_requests_id(self):
        for order in self:
            purchase_sign_requests_id = order.purchase_sign_requests_ids.filtered(lambda r: r.state not in ('cancel', 'refuse'))
            order.purchase_sign_requests_id = purchase_sign_requests_id[0] if purchase_sign_requests_id else False

    @api.depends('purchase_sign_requests_id', 'purchase_sign_requests_id.trp_approve_history_ids')
    def _compute_purchase_sign_requests_history_ids(self):
        for order in self:
            if order.purchase_sign_requests_id:
                # Chuyển One2many recordset thành list of IDs cho Many2many
                order.purchase_sign_requests_history_ids = [(6, 0, order.purchase_sign_requests_id.trp_approve_history_ids.ids)]
            else:
                order.purchase_sign_requests_history_ids = [(6, 0, [])]

    @api.depends('purchase_sign_requests_ids', 'purchase_sign_requests_ids.state')
    def _compute_purchase_sign_requests_count(self):
        for order in self:
            # Chỉ đếm các yêu cầu ký đang thực hiện (không tính cancel)
            active_requests = order.purchase_sign_requests_ids.filtered(lambda r: r.state not in ('cancel', 'refuse'))
            order.purchase_sign_requests_count = len(active_requests)

    def action_create_purchase_sign_request(self, resubmit=False):
        self.ensure_one()
        
        # Kiểm tra xem có yêu cầu ký nào đang thực hiện không
        active_request = self.env['purchase.sign.requests'].search([
            ('purchase_order_id', '=', self.id),
            ('state', 'not in', ['cancel', 'refuse'])
        ], limit=1)
        
        if active_request and not resubmit:
            raise UserError('Đơn mua hàng này đã có yêu cầu ký đang thực hiện. Chỉ được tạo yêu cầu mới khi yêu cầu hiện tại đã hủy.')
        
        # Nếu là trình ký lại, hủy yêu cầu cũ
        if resubmit and active_request:
            if active_request.state != 'approved':
                raise UserError('Chỉ có thể trình ký lại khi yêu cầu ký đã được duyệt.')
            old_request = active_request
            old_request.action_cancel()
        
        # Tao purchase sign request
        purchase_sign_request = self.env['purchase.sign.requests'].create({
            'purchase_order_id': self.id,
            'date': fields.Date.context_today(self),
            'date_planned': self.date_planned,
            'date_approve': self.date_approve,
            'amount_untax_total': self.amount_untaxed,
            'amount_tax_total': self.amount_tax,
            'amount_total': self.amount_total,
            'currency_id': self.currency_id.id,
            'debit': self.partner_id.debit,
            'description': self.description,
        })
        purchase_sign_request._onchange_purchase_order_id()
        purchase_sign_request.action_confirm()
        
        # Thông báo nếu là trình ký lại
        if resubmit and active_request:
            self.message_post(
                body=f"Đã trình ký lại yêu cầu ký. Yêu cầu cũ {active_request.name} đã được hủy, yêu cầu mới {purchase_sign_request.name} đã được tạo.",
            )
        
        return {
            'name': 'Yêu cầu ký',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.sign.requests',
            'res_id': purchase_sign_request.id,
            'target': 'current',
        }

    def action_resubmit_purchase_sign_request(self):
        """Trình ký lại - sử dụng lại action_create_purchase_sign_request với resubmit=True"""
        return self.action_create_purchase_sign_request(resubmit=True)

    def action_view_purchase_sign_requests(self):
        self.ensure_one()
        if self.purchase_sign_requests_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Yêu cầu ký',
                'view_mode': 'form',
                'res_model': 'purchase.sign.requests',
                'res_id': self.purchase_sign_requests_id.id,
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Yêu cầu ký',
                'view_mode': 'tree,form',
                'res_model': 'purchase.sign.requests',
                'domain': [('id', 'in', self.purchase_sign_requests_ids.ids)],
                'context': {
                    'default_purchase_order_id': self.id,
                }
            }

    def get_report_purchaseorder_2025_docx_context(self):
        res = super(PurchaseOrder, self).get_report_purchaseorder_2025_docx_context()
        
        history_ids = self.purchase_sign_requests_history_ids
        is_sign = bool(history_ids.mapped('approve_user_id'))
        if is_sign:
            approve_user_id = history_ids[0].approve_user_id if history_ids else False
            res['signer'] = {
                'sign': approve_user_id.sudo().sign_signature if is_sign else False,
                'name': approve_user_id.sudo().name_without_position,
            }
        else:
            res['signer'] = {
                'sign': False,
                'name': '',
            }
        
        return res

    def button_done(self):
        self.button_confirm()
        res = super(PurchaseOrder, self).button_done()
        for order in self:
            picking_ids = order.picking_ids.filtered(lambda p: p.state not in ['cancel','done'])
            if picking_ids:
                picking_ids.action_reset_to_draft()
                picking_ids.unlink()
        return res

    def action_create_picking_po(self):
        self._create_picking()

    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        if self.chief_accountant_id:
            res['chief_acc_id'] = self.chief_accountant_id.id
            
        unit_head_id = self.unit_head_id.id
        history_ids = self.purchase_sign_requests_history_ids.filtered(lambda x: x.approve_user_id)
        if history_ids:
            unit_head_id = history_ids[0].approve_user_id.id
            
        if unit_head_id:
            res['unit_heads_id'] = unit_head_id
            
        if self.description:
            res['reason_output_input_stock'] = self.description
            
        return res
