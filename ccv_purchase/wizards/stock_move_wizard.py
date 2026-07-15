from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime
import logging

_logger  = logging.getLogger(__name__)

class StockMoveWizard(models.TransientModel):
    _name = 'stock.move.wizard'
    _description = 'Wizard to create stock moves for purchase orders'

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order")
    default_location_id = fields.Many2one('stock.location', string="Kho kiểm kê")
    location_id = fields.Many2one('stock.location', string="Kho chốt lô", required=True)
    date = fields.Datetime(string="Thời gian chốt lô")
    line_ids = fields.One2many('stock.move.wizard.line', 'wizard_id', string="Adjustment Lines")

    def _get_wizard_lines_values(self, purchase_order, location_record):
        """
        Hàm helper để tính toán các giá trị cho các dòng wizard.
        Được tách ra để tái sử dụng trong default_get và onchange.
        """
        lines_vals = []
        for line in purchase_order.order_line:
            # --- BẮT ĐẦU LOGIC TÍNH TOÁN ---
            # 1. Tính toán số lượng
            delivered_qty = line.qty_received
            invoiced_qty = line.qty_invoiced
            diff_qty = abs(invoiced_qty - delivered_qty)
            
            # 2. Tính toán giá
            price_unit = line.price_unit
            price_total = abs(diff_qty) * price_unit
            
            # 3. Xác định tài khoản hạch toán
            credit_account_id = False
            debit_account_id = False
            if location_record:
                if diff_qty < 0:  # thiếu hàng -> Nhập kho
                    credit_account_id = line.product_id.categ_id.property_stock_valuation_account_id.id
                    debit_account_id = location_record.valuation_in_account_id.id
                elif diff_qty > 0:  # Thiếu hàng -> Xuất kho
                    credit_account_id = location_record.valuation_out_account_id.id
                    debit_account_id = line.product_id.categ_id.property_stock_valuation_account_id.id
            # --- KẾT THÚC LOGIC TÍNH TOÁN ---

            # Tạo dictionary giá trị cho dòng wizard
            line_vals = {
                'purchase_line_id': line.id,
                'product_id': line.product_id.id,
                'location_id': location_record.id if location_record else False,
                'delivered_qty': delivered_qty,
                'invoiced_qty': invoiced_qty,
                'diff_qty': diff_qty,
                'price_unit': price_unit,
                'price_total': price_total,
                'credit_account_id': credit_account_id,
                'debit_account_id': debit_account_id,
            }
            lines_vals.append(line_vals)
        return lines_vals

    @api.model
    def default_get(self, fields_list):
        res = super(StockMoveWizard, self).default_get(fields_list)
        # Chỉ lấy các giá trị mặc định, không tạo line_ids ở đây.
        # line_ids sẽ được tạo bởi hàm onchange.
        if self.env.context.get('active_model') == 'purchase.order' and self.env.context.get('active_id'):
            purchase_order = self.env['purchase.order'].browse(self.env.context.get('active_id'))
            
            # Lấy location_id từ system parameter
            location_id_param = self.env['ir.config_parameter'].sudo().get_param('ccv_purchase.default_location_dest_id')
            
            if location_id_param:
                try:
                    res['location_id'] = int(location_id_param)
                except (ValueError, TypeError):
                    pass # Bỏ qua nếu param không phải là số
            
            res['date'] = datetime.datetime.now()
            res['purchase_order_id'] = purchase_order.id
            res['default_location_id'] = purchase_order.picking_type_id.default_location_dest_id.id
            
        return res

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        """
        Khi đơn mua hàng thay đổi, tính toán lại các dòng.
        """
        if self.purchase_order_id:
            location_record = self.location_id
            
            # Gọi hàm helper để lấy giá trị các dòng
            lines_data = self._get_wizard_lines_values(self.purchase_order_id, location_record)
            
            # Cập nhật lại trường One2many
            self.line_ids = [(0, 0, vals) for vals in lines_data]

    def create_stock_moves(self):
        picking_obj = self.env['stock.picking']

        order_id = self.purchase_order_id
        body = "Điều chuyển được tạo: %s" % (order_id._get_html_link())
        rate = 1.0
        if hasattr(order_id, 'apply_manual_currency_exchange') and order_id.apply_manual_currency_exchange:
            if hasattr(order_id, 'inverse_manural_currency_exchange_rate'):
                rate = order_id.inverse_manural_currency_exchange_rate
        # Lọc các dòng sản phẩm Thừa
        missing_lines = self.line_ids.filtered(lambda l: l.type == 'lack')
        # Lọc các dòng sản phẩm thiếu
        extra_lines = self.line_ids.filtered(lambda l: l.type == 'extra')

        picking_type_id_param = self.env['ir.config_parameter'].sudo().get_param('ccv_purchase.picking_type')
        picking_type_id = int(picking_type_id_param) if picking_type_id_param else False

        # 1. Xử lý trường hợp thừa hàng (tạo phiếu xuất kho)
        if extra_lines:
            location_source = self.location_id
            location_dest = self.default_location_id
            
            picking = picking_obj.create({
                'picking_type_id': picking_type_id,
                'location_id': location_source.id,
                'location_dest_id': location_dest.id,
                'origin': self.purchase_order_id.name,
                'partner_id': self.purchase_order_id.partner_id.id,
                'need_create_invoice': False,
                'date': self.date,
                'stock_date_receipt': self.date,
                'reason_output_input_stock': _('Phiếu điều chỉnh thừa hàng từ đơn mua %s') % self.purchase_order_id.name,
            })
            
            for line in extra_lines:
                move_name = _('Chốt lô thừa %.3f tấn, Hoá đơn %s, PO %s') % \
                    (abs(line.diff_qty), line.purchase_line_id.order_id.invoice_ids and line.purchase_line_id.order_id.invoice_ids[0].name or 'N/A', self.purchase_order_id.name)
                self.env['stock.move'].create({
                    'name': move_name,
                    'picking_id': picking.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': abs(line.diff_qty),
                    'quantity_done': abs(line.diff_qty),
                    'product_uom': line.purchase_line_id.product_uom.id,
                    'location_id': location_source.id,
                    'location_dest_id': location_dest.id,
                    'price_unit': line.price_unit * rate,
                    'picking_type_id': picking_type_id,
                    'purchase_line_id': line.purchase_line_id.id,
                })
            
            picking.action_confirm()
            picking.button_validate()
            picking.message_post(body=body)
            self.handle_lines_picking(extra_lines, picking)
            self.purchase_order_id.picking_ids |= picking

        # 2. Xử lý trường hợp thiếu hàng (tạo phiếu nhập kho)
        if missing_lines:
            location_source = self.default_location_id
            location_dest = self.location_id
            
            picking = picking_obj.create({
                'picking_type_id': picking_type_id,
                'location_id': location_source.id,
                'location_dest_id': location_dest.id,
                'origin': self.purchase_order_id.name,
                'partner_id': self.purchase_order_id.partner_id.id,
                'date': self.date,
                'need_create_invoice': False,
                'stock_date_receipt': self.date,
                'reason_output_input_stock': _('Phiếu điều chỉnh thiếu hàng từ đơn mua %s') % self.purchase_order_id.name,
            })
            
            for line in missing_lines:
                move_name = _('Chốt lô thiếu %.3f tấn, Hoá đơn %s, PO %s') % \
                    (abs(line.diff_qty), line.purchase_line_id.order_id.invoice_ids and line.purchase_line_id.order_id.invoice_ids[0].name or 'N/A', self.purchase_order_id.name)
                self.env['stock.move'].create({
                    'name': move_name,
                    'picking_id': picking.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': abs(line.diff_qty),
                    'quantity_done': abs(line.diff_qty),
                    'product_uom': line.purchase_line_id.product_uom.id,
                    'location_id': location_source.id,
                    'location_dest_id': location_dest.id,
                    'price_unit': line.price_unit * rate,
                    'picking_type_id': picking_type_id,
                    'purchase_line_id': line.purchase_line_id.id,
                    'to_refund': True,
                })

            picking.action_confirm()
            picking.button_validate()
            picking.message_post(body=body)
            self.handle_lines_picking(missing_lines, picking)
            self.purchase_order_id.picking_ids |= picking

        return {'type': 'ir.actions.act_window_close'}

    def handle_lines_picking(self, lines, picking):
        move_ids = picking.move_ids
        svls = move_ids.stock_valuation_layer_ids.sudo()
        for svl in svls:
            svl.unit_cost = svl.stock_move_id.price_unit
            svl.value = svl.quantity * svl.unit_cost
        for line in lines:
            move_ids = picking.move_ids.filtered(lambda l: l.purchase_line_id == line.purchase_line_id)
            ams = move_ids.mapped('account_move_ids')
            for am in ams:
                svl = am.stock_valuation_layer_ids[0] if am.stock_valuation_layer_ids else False
                to_write = []
                if svl:
                    for aml in am.line_ids:
                        if aml.balance < 0:
                            to_write.append((1, aml.id, {
                                'account_id': line.credit_account_id.id,
                                'debit': 0,
                                'credit': abs(svl.unit_cost * svl.quantity),
                                'amount_currency': abs(svl.unit_cost * svl.quantity) * -1,
                            }))
                        else:
                            to_write.append((1, aml.id, {
                                'account_id': line.debit_account_id.id,
                                'debit': abs(svl.unit_cost * svl.quantity),
                                'credit': 0,
                                'amount_currency': abs(svl.unit_cost * svl.quantity),
                            }))
                    am.sudo().write({'line_ids': to_write})
