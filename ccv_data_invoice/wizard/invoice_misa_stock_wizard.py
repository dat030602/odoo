from odoo import models, fields, api
import logging

from odoo.exceptions import UserError

_logger  = logging.getLogger(__name__)

class InvoiceMisaStockWizard(models.TransientModel):
    _name = 'invoice.misa.stock.wizard'
    _description = 'Wizard to create stock moves for purchase orders'

    purchase_order_ids = fields.Many2many('purchase.order', string="Purchase Order")
    purchase_order_id = fields.Many2one('purchase.order', string="Đơn hàng", domain="[('id','in',purchase_order_ids)]")
    invoice_data_id = fields.Many2one('invoice.data', string="Invoice data")
    picking_type_id = fields.Many2one('stock.picking.type', string="Loại phiếu")
    location_dest_id = fields.Many2one('stock.location', string="Vị trí đích")
    date = fields.Datetime('Ngày dùng tồn')
    line_ids = fields.One2many('invoice.misa.stock.wizard.line', 'wizard_id', string="Adjustment Lines")

    def _get_wizard_lines_values(self):
        """
        Hàm helper để tính toán các giá trị cho các dòng wizard.
        Được tách ra để tái sử dụng trong default_get và onchange.
        """
        lines_vals = []
        if not self.invoice_data_id or not self.purchase_order_id:
            return lines_vals
        for line in self.invoice_data_id.ds_hhdv_m2o_ids.filtered(lambda invoice_line: invoice_line.so_luong > 0):
            purchase_line = self.purchase_order_id.order_line.filtered(lambda po_line: po_line.product_id == line.product_id)
            if purchase_line:
                purchase_line = purchase_line[0]
            else:
                continue
            line_vals = {
                'purchase_line_id': purchase_line.id,
                'product_id': line.product_id.id,
                'quantity': min(line.so_luong, purchase_line.product_qty),
                'price_unit': line.don_gia,
            }
            lines_vals.append(line_vals)
        return lines_vals

    @api.model
    def default_get(self, fields_list):
        res = super(InvoiceMisaStockWizard, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'invoice.data' and self.env.context.get('active_id'):
            invoice_data = self.env['invoice.data'].browse(self.env.context.get('active_id'))
            res['date'] = invoice_data.ngay_lap.strftime("%Y-%m-%d 07:00:00")
            purchase_order_ids = invoice_data.mapped('purchase_order_ids.id')
            res['purchase_order_ids'] = [(6, 0, purchase_order_ids)]
            res['purchase_order_id'] = purchase_order_ids[0] if purchase_order_ids else False
            res['invoice_data_id'] = invoice_data.id
        return res

    @api.onchange('purchase_order_id', 'invoice_data_id')
    def _onchange_purchase_order_id(self):
        """
        Khi đơn mua hàng hoặc invoice data thay đổi, tính toán lại các dòng.
        """
        self.line_ids = [(5, 0, 0)]
        if self.purchase_order_id and self.invoice_data_id:
            self.picking_type_id = self.purchase_order_id.picking_type_id.id
            lines_data = self._get_wizard_lines_values()
            self.line_ids = [(0, 0, vals) for vals in lines_data]

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id(self):
        if self.picking_type_id:
            self.location_dest_id = self.picking_type_id.default_location_dest_id.id

    def create_stock_moves(self):
        if not self.line_ids:
            raise UserError("Không có sản phẩm để tạo !!!")
        picking_type_id = self.picking_type_id

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type_id.id,
            'location_id': picking_type_id.default_location_src_id.id,
            'location_dest_id': self.location_dest_id.id,
            'origin': self.purchase_order_id.name,
            'partner_id': self.purchase_order_id.partner_id.id,
            'date': self.date,
            'need_create_invoice': False,
            'stock_date_receipt': self.date,
        })
        
        for line in self.line_ids:
            self.env['stock.move'].create({
                'name': line.product_id.name,
                'picking_id': picking.id,
                'product_id': line.product_id.id,
                'price_unit': line.price_unit,
                'purchase_line_id': line.purchase_line_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.purchase_line_id.product_uom.id,
                'picking_type_id': picking_type_id.id,
                'location_id': picking_type_id.default_location_src_id.id,
                'location_dest_id': self.location_dest_id.id,
            })
        body = "Điều chuyển được tạo: %s" % self.purchase_order_id._get_html_link()
        picking.message_post(body=body)
        body = "Hoá đơn điện tử: %s" % self.invoice_data_id._get_html_link()
        picking.message_post(body=body)
        self.purchase_order_id.picking_ids |= picking
        self.invoice_data_id.picking_ids |= picking 

        return {'type': 'ir.actions.act_window_close'}
