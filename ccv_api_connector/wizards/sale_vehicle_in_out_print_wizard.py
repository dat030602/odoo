from odoo import models, fields, api, _
from odoo.exceptions import UserError

import base64
import io
import zipfile

class SaleVehicleInOutPrintWizard(models.TransientModel):
    _name = 'sale.vehicle.in.out.print.wizard'
    _description = 'In phiếu theo xe'

    sale_vehicle_id = fields.Many2one('sale.vehicle.in.out', string="Phiếu điều xe", default=lambda self: self.env.context.get('active_id'))
    print_type = fields.Selection([
        ('delivery', 'Phiếu xuất kho giao hàng'),
        ('receipt', 'Phiếu nhập kho CCV'),
        ('ccv_transfer', 'Phiếu chuyển kho CCV')
    ], string="Loại phiếu")

    file_data = fields.Binary('Tệp tải xuống', readonly=True)
    file_name = fields.Char('Tên tệp')
    is_download = fields.Boolean(default=False)

    @api.model
    def _get_vehicle_nums(self):
        context = self.env.context
        sale_vehicle_id = context.get('default_sale_vehicle_id') or context.get('active_id')
        print_type = context.get('default_print_type')
        
        if sale_vehicle_id:
            domain = [('sale_vehicle_id', '=', sale_vehicle_id)]
            if print_type == 'delivery':
                domain.append(('type', '=', 'out'))
            elif print_type == 'receipt':
                domain.append(('type', '=', 'in'))
            # For ccv_transfer, we might want to include all types or just transfer. 
            # I'll leave it without type filter for ccv_transfer if not explicitly required, or add if needed.
            
            lines = self.env['sale.vehicle.in.out.line'].search(domain)
            nums = lines.mapped('vehicle_num')
            return [(num, num) for num in set(nums) if num]
        
        # Fallback during database flush when context is lost
        self.env.cr.execute("SELECT DISTINCT vehicle_num FROM sale_vehicle_in_out_line WHERE vehicle_num IS NOT NULL")
        nums = [r[0] for r in self.env.cr.fetchall() if r[0]]
        return [(num, num) for num in nums]

    vehicle_num = fields.Selection(selection='_get_vehicle_nums', string="Số xe", required=True)

    def action_print(self):
        self.ensure_one()
        if not self.vehicle_num:
            raise UserError(_("Vui lòng chọn số xe."))
        
        domain = [
            ('sale_vehicle_id', '=', self.sale_vehicle_id.id),
            ('vehicle_num', '=', self.vehicle_num)
        ]
        if self.print_type == 'delivery':
            domain.append(('type', '=', 'out'))
        elif self.print_type == 'receipt':
            domain.append(('type', '=', 'in'))
            
        lines = self.env['sale.vehicle.in.out.line'].search(domain)
        pickings = lines.mapped('picking_id')

        if not pickings:
            raise UserError(_("Không tìm thấy phiếu kho (picking) nào cho xe %s." % self.vehicle_num))

        if self.print_type == 'delivery':
            action = self.env.ref('biz_ccv_sale.action_report_stock_picking_new_docx').report_action(pickings.ids)
            return action
        elif self.print_type == 'receipt':
            action = self.env.ref('biz_ccv_sale.action_rp_ccv_warehouse_receipt').report_action(pickings.ids)
            return action
        elif self.print_type == 'ccv_transfer':
            action = self.env.ref('biz_ccv_sale.action_report_stock_picking_ccv_warehouse_transfer_note').report_action(pickings.ids)
            return action
