from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    price_unit_src = fields.Float(string="Đơn giá gốc", digits='Product Price', store=True)
    price_unit_bonus = fields.Float(string="Quỹ dự phòng", digits='Product Price', compute="_compute_price_unit_bonus", store=True)
    bonus_price_id = fields.Many2one('sale.bonus.price.unit', string="Quỹ dự phòng", related="order_id.bonus_price_id")
    promotion_ccv_id = fields.Many2one('sale.ccv.promotion', string="Khuyến mãi",  related='order_id.promotion_ccv_id')
    promotion_ccv_amount = fields.Float(string="Khuyến mãi")
    is_adjusted_pricelist = fields.Boolean(
        string="Là bảng giá điều chỉnh",
        related="order_id.is_adjusted_pricelist",
        store=True,
    )

    qty_ordered = fields.Float(string='ĐH đã duyệt SL', digits='Product Unit of Measure')
    qty_order_delivered = fields.Float(string='ĐH đã giao SL', digits='Product Unit of Measure')
    qty_can_order = fields.Float(string='còn lại SL', digits='Product Unit of Measure', compute='_compute_qty_can_order', store=True)
    is_over_ordered = fields.Boolean(string='Quá SL còn lại', compute='_compute_is_over_ordered', store=True)

    @api.depends('product_uom_qty', 'qty_can_order')
    def _compute_is_over_ordered(self):
        for line in self:
            line.is_over_ordered = line.product_uom_qty > line.qty_can_order

    @api.onchange('product_id')
    def _onchange_product_id_qty_ordered(self):
        for line in self:
            line.qty_ordered = line.product_id.with_context(warehouse=line.order_id.warehouse_id.id).qty_ordered
            line.qty_order_delivered = line.product_id.with_context(warehouse=line.order_id.warehouse_id.id).qty_order_delivered

    @api.depends('qty_ordered', 'qty_order_delivered', 'order_id.warehouse_id')
    def _compute_qty_can_order(self):
        for line in self:
            line.qty_can_order = line.product_id.with_context(warehouse=line.order_id.warehouse_id.id).qty_can_order

    @api.onchange('promotion_ccv_id', 'price_unit_src', 'is_promotional_product')
    def _onchange_promotion_price(self):
        for rec in self:
            if rec.is_promotional_product:
                rec.promotion_ccv_amount = 0
            elif rec.promotion_ccv_id:
                if rec.promotion_ccv_id.type == 'percentage':
                    # Calculate percentage based on Original Price
                    rec.promotion_ccv_amount = rec.price_unit_src * rec.promotion_ccv_id.amount_percentage / 100
                elif rec.promotion_ccv_id.type == 'gift':
                    rec.promotion_ccv_amount = 0
                else:
                    rec.promotion_ccv_amount = rec.promotion_ccv_id.amount
            else:
                rec.promotion_ccv_amount = 0

    @api.depends('order_id.bonus_price_id', 'product_id', 'is_promotional_product')
    def _compute_price_unit_bonus(self):
        for rec in self:
            if rec.bonus_price_id and not rec.is_promotional_product and rec._check_can_apply_bonus_price_unit():
                rec.price_unit_bonus = rec.bonus_price_id.amount
            else:
                rec.price_unit_bonus = 0

    @api.onchange('is_promotional_product', 'bonus_price_id', 'price_unit_src')
    def _onchange_bonus_price(self):
        """
        Called by sale.order onchange
        """
        for rec in self:
            rec._compute_price_unit_bonus()
            rec._onchange_update_actual_price()

    @api.onchange('price_unit_src', 'price_unit_bonus', 'promotion_ccv_amount')
    def _onchange_update_actual_price(self):
        """
        MASTER LOGIC: Actual Price = Original Price + Bonus + Promotion
        This ensures price_unit_src stays fixed when bonus changes.
        """
        for rec in self:
            rec.price_unit = rec.price_unit_src + rec.price_unit_bonus + rec.promotion_ccv_amount

    def _check_can_apply_bonus_price_unit(self):
        self.ensure_one()
        bonus_price_id = self.bonus_price_id
        if not bonus_price_id:
            return False
        return self.product_id.categ_id in bonus_price_id.categ_ids

    @api.onchange('product_id', 'product_uom', 'product_uom_qty')
    def _onchange_product_id_set_price_src(self):
        """
        Initial capture from Pricelist to Original Price
        """
        if self.product_id:
            res = super(SaleOrderLine, self)._get_display_price()
            self.price_unit_src = res
            # Trigger subsequent updates
            self._compute_price_unit_bonus()
            self._onchange_promotion_price()
            self._onchange_update_actual_price()

    def action_open_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.order_id.display_name,
            'res_model': 'sale.order',
            'view_mode': 'form',
            'target': 'current',
            'res_id': self.order_id.id,
        }

    def _check_line_unlink(self):
        res = super(SaleOrderLine, self)._check_line_unlink()
        if not res:
            return self.filtered(
                lambda line:
                    line.state in ('sale', 'done')
                    and line.product_uom_qty > 0
                    and (line.invoice_lines or not line.is_downpayment)
                    and not line.display_type
            )

    @api.onchange('product_id', 'product_uom_qty', 'price_unit')
    def _onchange_product_id_gift_promotion(self):
        for rec in self:
            if rec.order_id and rec.order_id.promotion_ccv_id and rec.order_id.promotion_ccv_id.type == 'gift':
                rec.order_id.promotion_ccv_id._apply_gift_to_order(rec.order_id.id)

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SaleOrderLine, self).create(vals_list)
        # Auto-correct price_unit on creation for all users
        # Fix: Populate price_unit_src if created programmatically (e.g. from Quotation Template)
        for line in res:
            if not line.price_unit_src and line.product_id:
                line.price_unit_src = line._get_display_price()

            if not line.price_unit_src:
                continue
            expected_price = line.price_unit_src + (line.price_unit_bonus or 0.0) + (line.promotion_ccv_amount or 0.0)
            if abs((line.price_unit or 0.0) - expected_price) > 0.01:
                line.with_context(skip_safe_price_recompute=True, pass_change_price_unit=True).sudo().write({'price_unit': expected_price})
        return res

    def write(self, vals):
        ctx = self.env.context
        is_allowed_user = self.env.user.login == 'tannt@ccv.vn'

        # Chặn sửa price_unit_src dựa trên phân quyền Bảng báo giá:
        # Chỉ Trưởng khu vực (group_hide_cancel_button) mới được sửa giá gốc
        # và chỉ khi đơn hàng đang dùng bảng giá 'BBG Điều Chỉnh'
        if 'price_unit_src' in vals and not is_allowed_user and not ctx.get('pass_change_price_unit'):
            has_group = self.env.user.has_group('ccv_sale.group_hide_cancel_button')
            all_allowed = True
            for line in self:
                # Trưởng khu vực được phép sửa giá tự do trên bảng giá BBG Điều Chỉnh
                if has_group and line.order_id.pricelist_id.name == 'BBG Điều Chỉnh':
                    continue
                
                # Hợp lệ nếu price_unit_src mới trùng khớp với giá trị được tính toán từ bảng giá hiện tại (automatic update)
                product = self.env['product.product'].browse(vals.get('product_id')) if 'product_id' in vals else line.product_id
                qty = vals.get('product_uom_qty') if 'product_uom_qty' in vals else line.product_uom_qty
                uom = self.env['uom.uom'].browse(vals.get('product_uom')) if 'product_uom' in vals else line.product_uom
                pricelist = line.order_id.pricelist_id
                
                if product and pricelist:
                    try:
                        pricelist_price = pricelist._get_product_price(
                            product,
                            qty or 1.0,
                            uom=uom or product.uom_id,
                            date=line.order_id.date_order
                        )
                        new_price_src = float(vals.get('price_unit_src') or 0.0)
                        if abs(new_price_src - pricelist_price) < 0.01:
                            continue
                    except Exception as e:
                        _logger.warning("Failed to compute pricelist price in write check: %s", str(e))
                
                # Nếu không thuộc các trường hợp trên, đây là hành vi sửa tay không hợp lệ
                all_allowed = False
                break

            if not all_allowed:
                vals.pop('price_unit_src', None)

        # Block price_unit changes on approved sign requests (per-record safe)
        for line in self:
            if line.order_id.sale_sign_requests_ids.filtered(lambda r: r.state == 'approved').exists():
                if not is_allowed_user and not ctx.get('pass_change_price_unit', False):
                    vals.pop('price_unit', None)
                    vals.pop('price_unit_src', None)
                    break
        res = super(SaleOrderLine, self).write(vals)
        # Auto-correct price_unit on write for all users
        # Only trigger when price-related fields were written (or bonus was recomputed)
        price_related_fields = {'price_unit', 'price_unit_src', 'price_unit_bonus', 'promotion_ccv_amount', 'product_id', 'bonus_price_id'}
        if not price_related_fields.isdisjoint(vals) and not ctx.get('skip_safe_price_recompute', False):
            for line in self:
                if not line.price_unit_src:
                    continue
                expected_price = line.price_unit_src + (line.price_unit_bonus or 0.0) + (line.promotion_ccv_amount or 0.0)
                if abs((line.price_unit or 0.0) - expected_price) > 0.01:
                    line.with_context(skip_safe_price_recompute=True, pass_change_price_unit=True).sudo().write({'price_unit': expected_price})
        return res

