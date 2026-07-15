from odoo import models, fields, api, _
from odoo.exceptions import UserError

class GroupTransportInvoiceWizard(models.TransientModel):
    _name = 'group.transport.invoice.wizard'
    _description = 'Gộp tạo hóa đơn vận chuyển'

    def action_create_invoice(self):
        ticket_ids = self.env.context.get('active_ids', [])
        tickets = self.env['transport.ticket'].browse(ticket_ids)
        
        if not tickets:
            raise UserError(_("Không có phiếu vận chuyển nào được chọn!"))
            
        if any(t.state != 'draft' for t in tickets):
            raise UserError(_("Chỉ có thể gộp các phiếu vận chuyển đang ở trạng thái Nháp!"))
            
        # Group by partner
        partner_ids = tickets.mapped('partner_id')
        if len(partner_ids) > 1:
            raise UserError(_("Chỉ có thể gộp các phiếu vận chuyển của cùng một Nhà xe (Đối tác)!"))
            
        partner = partner_ids[0]
        
        # Determine note
        stock_inputs = self.env['purchase.order.stock.input'].search([
            ('picking_id', 'in', tickets.mapped('picking_id').ids),
            ('state', '=', 'done'),
            ('unload_container_id', '!=', False),
            ('is_sale', '=', False)
        ])
        
        po_ids = tickets.mapped('purchase_id')
        if stock_inputs and len(po_ids) == 1:
            note = po_ids[0]._get_note_invoice(stock_inputs)
        else:
            note = "Chi phí vận chuyển"
            
        # Create vendor bill
        move_vals = {
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.context_today(self),
            'note': note,
            'invoice_line_ids': []
        }
        
        for ticket in tickets:
            product = ticket.unload_container_id
            if not product:
                raise UserError(_("Phiếu %s chưa chọn dịch vụ vận chuyển!") % ticket.name)
                
            # Must use TK 3351
            account_3351 = self.env['account.account'].search([
                ('code', '=', '3351'), 
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            
            if account_3351:
                account_id = account_3351.id
            else:
                account_id = product.property_account_expense_id.id or product.categ_id.property_account_expense_categ_id.id
                
            if not account_id:
                raise UserError(f"Sản phẩm dịch vụ {product.name} chưa được cấu hình tài khoản chi phí!")
                
            line_vals = (0, 0, {
                'product_id': product.id,
                'name': note,
                'account_id': account_id,
                'quantity': ticket.quantity,
                'price_unit': ticket.price_unit,
            })
            move_vals['invoice_line_ids'].append(line_vals)
            
        move = self.env['account.move'].create(move_vals)
        
        # We must link back to the tickets. Since Odoo might reorder or add tax lines, 
        # we identify the lines we just added by product and quantity, or simply match them 
        # in the same order if we know there are no automatic tax lines yet, but to be 100% safe:
        # We will write the lines directly with their ticket reference in the name or context, 
        # or we just create them one by one.
        
        # Actually, since we created the move with invoice_line_ids in the create call, 
        # the lines are created. We can zip tickets with the lines if we filter out tax lines.
        product_lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        
        # It's safest to match by ticket.name since we embedded it in the line name.
        for ticket in tickets:
            matching_line = product_lines.filtered(lambda l: ticket.name in l.name)
            if matching_line:
                ticket.write({
                    'move_line_id': matching_line[0].id,
                    'state': 'invoiced',
                })
            
        return {
            'name': _('Hóa đơn Nhà xe'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current',
        }
