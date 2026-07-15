from odoo import models, fields, api
import logging
import re
from odoo.exceptions import ValidationError,UserError
import requests
import base64

def get_image_from_url(url):
    if url:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                return image_base64
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout, 
                requests.exceptions.RequestException) as e:
            _logger.warning("Failed to fetch QR image from URL %s: %s", url, str(e))
            return False
    return False


_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    bonus_price_id = fields.Many2one('sale.bonus.price.unit', string="Quỹ dự phòng", tracking=True)
    promotion_ccv_id = fields.Many2one('sale.ccv.promotion', string="Khuyến mãi")

    @api.onchange('partner_id')
    def _onchange_field_name(self):
        for rec in self:
            current_date = rec.date_order.date() if rec.date_order else False
            bonus_price_id = self.env['sale.bonus.price.unit']
            promotion_env = self.env['sale.ccv.promotion']
            promotion_ccv_id = promotion_env
            if rec.partner_id.team_id:
                # Quỹ dự phòng
                bonus_price_id = bonus_price_id.search([
                    ('team_id','=',rec.partner_id.team_id.id), 
                    ('date_from','<=',current_date),
                    ('date_to','>=',current_date),
                    ('partner_ids','in',rec.partner_id.ids)
                ],limit=1)
                # Khuyến mãi
                promotion_ccv = promotion_env.search([
                    ('date_from', '<=', current_date),
                    ('date_to', '>=', current_date),
                    ('team_id', '=', rec.partner_id.team_id.id),
                    ('is_default', '=', False),
                ])
                for promotion in promotion_ccv:
                    if promotion.partner_domain:
                        partner_ids = promotion._get_partner_by_domain()
                        if (not partner_ids) or (rec.partner_id in partner_ids):
                            promotion_ccv_id = promotion
                            break
            if not bonus_price_id:
                bonus_price_id = bonus_price_id.search([
                    ('team_id','=',rec.partner_id.team_id.id), 
                    ('date_from','<=',current_date),
                    ('date_to','>=',current_date),
                ],limit=1)
                if not bonus_price_id:
                    bonus_price_id = bonus_price_id.search([('team_id','=',False), ('date_from','<=',current_date),('date_to','>=',current_date)],limit=1)
            elif bonus_price_id and bonus_price_id.bonus_default_id.exists():
                bonus_price_id = False
            rec.bonus_price_id = bonus_price_id
            rec.promotion_ccv_id = promotion_ccv_id if promotion_ccv_id else promotion_env.search([('is_default','=',True)],limit=1)

    @api.onchange('bonus_price_id')
    def _onchange_bonus_price_id(self):
        self.order_line._onchange_bonus_price()

    @api.onchange('promotion_ccv_id')
    def _onchange_promotion_ccv_id(self):
        self.order_line._onchange_promotion_price()

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        # When bonus_price_id changes, force-recalculate price_unit on lines
        # for non-whitelisted users (e.g. Telesales) where price_unit is readonly in UI
        # and therefore the onchange-updated value is never sent to the server on save.
        if 'bonus_price_id' in vals:
            non_promo_lines = self.order_line.filtered(lambda l: not l.is_promotional_product)
            for line in non_promo_lines:
                if not line.price_unit_src:
                    continue
                expected = line.price_unit_src + (line.price_unit_bonus or 0.0) + (line.promotion_ccv_amount or 0.0)
                if abs(line.price_unit - expected) > 0.01:
                    line.with_context(skip_safe_price_recompute=True, pass_change_price_unit=True).sudo().write({'price_unit': expected})
        return res

    # @api.onchange('promotion_ccv_id')
    # def _onchange_promotion_ccv_id(self):
    #     """
    #     Tự động áp dụng hoặc xóa quà tặng khi thay đổi promotion
    #     """
    #     for rec in self:
    #         # Nếu không có promotion hoặc promotion không phải gift, xóa tất cả gift lines
    #         if not rec.promotion_ccv_id or rec.promotion_ccv_id.type != 'gift':
    #             gift_lines_to_remove = rec.order_line.filtered(lambda line: getattr(line, 'is_promotional_product', False))
    #             if gift_lines_to_remove:
    #                 gift_lines_to_remove.unlink()
    #         elif rec.promotion_ccv_id.type == 'gift':
    #             # Áp dụng gift promotion
    #             rec.promotion_ccv_id._apply_gift_to_order(rec.id)

    def _recompute_prices(self):
        super()._recompute_prices()
        for line in self._get_update_prices_lines():
            line.price_unit_src = line._get_display_price()
            expected = line.price_unit_src + (line.price_unit_bonus or 0.0) + (line.promotion_ccv_amount or 0.0)
            if abs(line.price_unit - expected) > 0.01:
                line.with_context(skip_safe_price_recompute=True, pass_change_price_unit=True).sudo().write({'price_unit': expected})


    ### QR Bank ###
    
    vietqr_bank_id = fields.Many2one('vietqr.bank.config', string="Ngân hàng")
    amount_bank = fields.Monetary(string="Số tiền", store=True, compute="_compute_amount_qr_bank",currency_field="currency_id")
    qr_url = fields.Char(string="QR Code")
    qr_image = fields.Binary(string="QR Code", attachment=False, stored=True, max_width=200, compute="_compute_qr")
    bank_info = fields.Char(string="Nội dung chuyển khoản", store=True, compute="_compute_bank_info",size=25)
    is_show_qr = fields.Char(string="QR Code", compute="_compute_is_show_qr")
    
    @api.depends('qr_url')
    def _compute_qr(self):
        for rec in self:
            try:
                rec.qr_image = get_image_from_url(rec.qr_url)
            except Exception as e:
                _logger.warning("Failed to compute QR image for sale order %s: %s", rec.name, str(e))
                rec.qr_image = False

    @api.depends('vietqr_bank_id')
    def _compute_is_show_qr(self):
        for rec in self:
            rec.is_show_qr = rec.vietqr_bank_id is not False
    
    def action_create_qr_code(self):
        self.ensure_one()
        if not self.vietqr_bank_id:
            raise UserError("Vui lòng chọn ngân hàng!!!")
        self.vietqr_bank_id.create_vietqr_qr_code(self)
        
    @api.depends('amount_total')
    def _compute_amount_qr_bank(self):
        for rec in self:
            rec.amount_bank = rec.amount_total
    
    @api.depends('invoice_ids.vat_sinvoice_number', 'name')
    def _compute_bank_info(self):
        for rec in self:
            invoice = " ".join([invoice.vat_sinvoice_number for invoice in rec.invoice_ids.filtered(lambda l:l.move_type == 'out_invoice' and l.payment_state not in ('paid','in_payment')) if invoice.vat_sinvoice_number])
            order_number = rec.name.split('/')
            if order_number:
                order_number = order_number[0]
                order_number = order_number[-6:]
            rec.bank_info = '%s DonHang %s' % (invoice, order_number)
    
    @api.onchange('state')
    def _onchange_state_vietqr_bank_id(self):
        for rec in self:
            if not self.vietqr_bank_id:
                rec.vietqr_bank_id = self.env['vietqr.bank.config'].search([('is_default','=',True)],limit=1)
    
    @api.constrains('bank_info')
    def _check_bank_info(self):
        for record in self:
            if record.bank_info and not re.match("^[A-Za-z0-9 ]*$", record.bank_info):
                raise ValidationError("Chỉ cho phép nhập chữ, số và khoảng trắng!")

    # Sale Sign Requests
    sale_sign_requests_ids = fields.One2many('sale.sign.requests', 'sale_order_id', string='Yêu cầu ký')
    sale_sign_requests_id = fields.Many2one('sale.sign.requests', 'Yêu cầu ký', compute='_compute_sale_sign_requests_id', store=True)
    sale_sign_requests_state = fields.Selection('Trạng thái duyệt', related='sale_sign_requests_id.state', store=True)
    sale_sign_requests_history_ids = fields.Many2many('trp.approve.history', 'sale_sign_requests_history_ids', string='Lịch sử duyệt', compute='_compute_sale_sign_requests_history_ids')
    sale_sign_requests_count = fields.Integer(string='Số yêu cầu ký', compute='_compute_sale_sign_requests_count')

    @api.depends('sale_sign_requests_ids')
    def _compute_sale_sign_requests_id(self):
        for order in self:
            sale_sign_requests_id = order.sale_sign_requests_ids.filtered(lambda r: r.state not in ('cancel', 'refuse'))
            order.sale_sign_requests_id = sale_sign_requests_id[0] if sale_sign_requests_id else False

    @api.depends('sale_sign_requests_id', 'sale_sign_requests_id.trp_approve_history_ids')
    def _compute_sale_sign_requests_history_ids(self):
        for order in self:
            if order.sale_sign_requests_id:
                # Chuyển One2many recordset thành list of IDs cho Many2many
                order.sale_sign_requests_history_ids = [(6, 0, order.sale_sign_requests_id.trp_approve_history_ids.ids)]
            else:
                order.sale_sign_requests_history_ids = [(6, 0, [])]

    @api.depends('sale_sign_requests_ids', 'sale_sign_requests_ids.state')
    def _compute_sale_sign_requests_count(self):
        for order in self:
            # Chỉ đếm các yêu cầu ký đang thực hiện (không tính cancel)
            active_requests = order.sale_sign_requests_ids.filtered(lambda r: r.state not in ('cancel', 'refuse'))
            order.sale_sign_requests_count = len(active_requests)

    def action_create_sale_sign_request(self, resubmit=False):
        self.ensure_one()
        
        # Kiểm tra xem có yêu cầu ký nào đang thực hiện không
        active_request = self.env['sale.sign.requests'].search([
            ('sale_order_id', '=', self.id),
            ('state', 'not in', ['cancel', 'refuse'])
        ], limit=1)
        
        if active_request and not resubmit:
            raise UserError('Đơn hàng này đã có yêu cầu ký đang thực hiện. Chỉ được tạo yêu cầu mới khi yêu cầu hiện tại đã hủy.')
        
        # Nếu là trình ký lại, hủy yêu cầu cũ
        if resubmit and active_request:
            if active_request.state != 'approved':
                raise UserError('Chỉ có thể trình ký lại khi yêu cầu ký đã được duyệt.')
            old_request = active_request
            old_request.action_cancel()
        
        # Tao sale sign request
        sale_sign_request = self.env['sale.sign.requests'].create({
            'sale_order_id': self.id,
            'date': fields.Date.context_today(self),
            'amount_untax_total': self.amount_untaxed,
            'amount_tax_total': self.amount_tax,
            'amount_total': self.amount_total,
            'currency_id': self.currency_id.id,
            'contact_total_due': self.contact_total_due,
            'credit_limit': self.credit_limit,
            'contact_phone': self.contact_phone,
            'contact_representative': self.contact_representative,
            'payment_term_id': self.payment_term_id.id,
            'payment_type': self.payment_type,
            'internal_note': self.internal_note,
            'user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'origin': self.origin,
            'sales_team_captain_id': self.sales_team_captain_id.id,
        })
        sale_sign_request._onchange_sale_order_id()
        sale_sign_request.action_confirm()
        
        # Thông báo nếu là trình ký lại
        if resubmit and active_request:
            self.message_post(
                body=f"Đã trình ký lại yêu cầu ký. Yêu cầu cũ {active_request.name} đã được hủy, yêu cầu mới {sale_sign_request.name} đã được tạo.",
            )
        
        return {
            'name': 'Yêu cầu ký',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.sign.requests',
            'res_id': sale_sign_request.id,
            'target': 'current',
        }

    def action_view_sale_sign_requests(self):
        self.ensure_one()
        if len(self.sale_sign_requests_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Yêu cầu ký',
                'view_mode': 'form',
                'res_model': 'sale.sign.requests',
                'res_id': self.sale_sign_requests_ids.id,
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Yêu cầu ký',
                'view_mode': 'tree,form',
                'res_model': 'sale.sign.requests',
                'domain': [('id', 'in', self.sale_sign_requests_ids.ids)],
                'context': {
                    'default_sale_order_id': self.id,
                }
            }

    def action_resubmit_sale_sign_request(self):
        """Trình ký lại - sử dụng lại action_create_sale_sign_request với resubmit=True"""
        return self.action_create_sale_sign_request(resubmit=True)

    def get_report_saleorder_2025_docx_context(self):
        res = super(SaleOrder, self).get_report_saleorder_2025_docx_context()
        # if not self.sale_sign_requests_id:
        #     return res

        history_ids = self.sale_sign_requests_history_ids
        
        # if not history_ids:
        #     return res
        config_id = history_ids.trp_approve_config_line_id.trp_approve_config_id
        
        # Danh sach cac nguoi duyệt
        approvers = [
            ('founder_id', self.founder_id),
            ('regional_head_id', self.regional_head_id),
            ('finance_account_dept_id', self.finance_account_dept_id),
            ('sale_manager_id', self.sale_manager_id),
            ('bod_id', self.bod_id),
        ]
        name = self.founder_id.sudo().name_without_position or self.founder_id.sudo().name
        is_sign = True
        res['founder_id'] = {
            'sign': self.founder_id.sudo().sign_signature if is_sign else False,
            'name': name,
        }
        
        if config_id and config_id.trp_approve_config_line_ids:
            # Process each approver with their corresponding config line
            config_lines = config_id.trp_approve_config_line_ids
            # approver_fields = ['regional_head_id', 'finance_account_dept_id', 'sale_manager_id', 'bod_id']
            for config_line in config_lines:
                field_name = config_line.approver_field
                history_id = history_ids.filtered(lambda history: history.trp_approve_config_line_id == config_line)
                approver = getattr(self, field_name, None)
                if history_id.approve_user_id:
                    approver = history_id.approve_user_id
                
                if approver:
                    name = approver.sudo().name_without_position or approver.sudo().name
                    is_sign = bool(history_id.approve_user_id)
                    
                    res[field_name] = {
                        'sign': approver.sudo().sign_signature if is_sign else False,
                        'name': name,
                    }
                else:
                    # Ensure all fields are always present in context, even if approver is None
                    # Get approver from approvers list for default name
                    approver_from_list = next((approver for field, approver in approvers if field == field_name), None)
                    default_name = approver_from_list.sudo().name_without_position or approver_from_list.sudo().name if approver_from_list else ''
                    res[field_name] = {
                        'sign': False,
                        'name': default_name,
                    }
        else:
            # Tao thong tin ky cho tung nguoi duyet
            for field_name, approver in approvers:
                if approver:
                    history_id = history_ids.filtered(lambda history: history.approve_user_id == approver)
                    name = approver.sudo().name_without_position or approver.sudo().name
                    
                    if field_name == 'founder_id':
                        is_sign = True
                        founder = self.founder_id
                        name = founder.sudo().name_without_position or founder.sudo().name
                    elif not history_ids:
                        is_sign = False
                    else:
                        is_sign = bool(history_id)
                        if history_id:
                            approver = history_id.approve_user_id
                            name = approver.sudo().name_without_position or approver.sudo().name
                    
                    res[field_name] = {
                        'sign': approver.sudo().sign_signature if is_sign else False,
                        'name': name,
                    }
                else:
                    res[field_name] = {
                        'sign': False,
                        'name': '',
                    }
        return res

    def _compute_hide_cancel_button(self):
        for rec in self:
            rec.hide_cancel_button = self.env.user.has_group('ccv_sale.group_hide_cancel_button')

    hide_cancel_button = fields.Boolean(
        string="Hide Cancel Button",
        compute="_compute_hide_cancel_button",
        store=False,
    )

    is_adjusted_pricelist = fields.Boolean(
        string="Là bảng giá điều chỉnh",
        compute="_compute_is_adjusted_pricelist",
        store=True,
    )

    @api.depends('pricelist_id')
    def _compute_is_adjusted_pricelist(self):
        for rec in self:
            rec.is_adjusted_pricelist = bool(rec.pricelist_id and rec.pricelist_id.name == 'BBG Điều Chỉnh')

    def action_cancel(self):
        for rec in self:
            if not rec.sale_sign_requests_id:
                continue
            if rec.sale_sign_requests_id.state in ('approved'):
                raise UserError("Đơn hàng này đã được duyệt. Không thể hủy.")
            if rec.sale_sign_requests_id.state in ('approve'):
                raise UserError("Đơn hàng này đang được duyệt. Không thể hủy.")
            if rec.sale_sign_requests_id.state not in ('draft'):
                rec.sale_sign_requests_id.action_cancel()
        return super(SaleOrder, self).action_cancel()
