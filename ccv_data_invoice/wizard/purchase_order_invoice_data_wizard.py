from odoo import fields, models, _
from odoo.exceptions import ValidationError


class PurchaseOrderInvoiceDataWizard(models.TransientModel):
    _name = 'purchase.order.invoice.data.wizard'
    _description = 'Chon hoa don dien tu cho don mua'

    purchase_order_id = fields.Many2one('purchase.order', string='Đơn mua hàng', required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', related='purchase_order_id.partner_id', readonly=True)
    invoice_data_id = fields.Many2one(
        'invoice.data',
        string='Hoá đơn',
        required=True,
        domain="['|',('nban_id', '=', partner_id),('nban_dt_cong_no', '=', partner_id)]",
    )

    def action_confirm(self):
        self.ensure_one()
        if not self.purchase_order_id or not self.invoice_data_id:
            raise ValidationError(_('Vui lòng chọn đơn mua và hóa đơn.'))
            
        # 1. Liên kết invoice.data với purchase.order
        self.invoice_data_id.write({'purchase_order_ids': [(4, self.purchase_order_id.id)]})
        
        # 2. Tìm các Phiếu kế toán (Vendor Bills) của Đơn mua hàng này
        # CHỈ lấy các phiếu chưa bị Hủy và CHƯA có Hóa đơn điện tử nào được gán
        moves = self.purchase_order_id.invoice_ids.filtered(
            lambda m: m.move_type in ['in_invoice', 'in_refund'] 
            and m.state != 'cancel'
            and not m.invoice_data_ids
        )
        
        if moves:
            # 3. Liên kết invoice.data với account.move
            moves.write({'invoice_data_ids': [(4, self.invoice_data_id.id)]})
            self.invoice_data_id.write({'created_invoice_ids': [(4, move.id) for move in moves]})
            
            # 4. Ghi đè thông tin VAT vào Phiếu kế toán (Giống logic wz.account.move.update.invoice.info)
            move_vals = {
                'ref': self.invoice_data_id.so_hoa_don,
            }
            if 'series' in moves._fields:
                move_vals['series'] = self.invoice_data_id.ky_hieu
            if 'date_invoice' in moves._fields:
                move_vals['date_invoice'] = self.invoice_data_id.ngay_lap
            if 'invoice_date' in moves._fields:
                move_vals['invoice_date'] = self.invoice_data_id.ngay_lap
            
            if move_vals:
                moves.write(move_vals)
                
            line_vals = {}
            lines = moves.line_ids
            if 'invoice_number' in lines._fields:
                line_vals['invoice_number'] = self.invoice_data_id.so_hoa_don
            if 'invoice_code' in lines._fields:
                line_vals['invoice_code'] = self.invoice_data_id.ky_hieu
            if 'date_invoice' in lines._fields:
                line_vals['date_invoice'] = self.invoice_data_id.ngay_lap
                
            if line_vals and lines:
                lines.write(line_vals)
                
        return self.purchase_order_id.action_view_supplier_invoices(self.invoice_data_id)

