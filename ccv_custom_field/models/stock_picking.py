from odoo import models, fields, api
import logging
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    description_export_import = fields.Text(string="Diễn giải",compute="_compute_description_picking")

    @staticmethod
    def html_to_text(html_content):
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n").strip()

    @api.depends('reason_output_input_stock')
    def _compute_description_picking(self):
        for rec in self:
            description = ''
            if rec.reason_output_input_stock:
                reason = rec.reason_output_input_stock
                description = self.html_to_text(reason)
            rec.description_export_import = description

    def _get_id_sign(self):
        voter_id                = self.sudo().env.ref("ccv_custom_field.default_voter_id").value
        voter_id2               = self.sudo().env.ref("ccv_custom_field.default_voter_id2").value
        business_department_id  = self.sudo().env.ref("ccv_custom_field.default_business_department_id").value,
        stocker_id              = self.sudo().env.ref("ccv_custom_field.default_stocker_id").value,
        unit_heads_id           = self.sudo().env.ref("ccv_custom_field.default_unit_heads_id").value
        chief_acc_id            = self.sudo().env.ref("ccv_custom_field.default_chief_acc_id").value

        voter_id                = voter_id[0]                  if isinstance(voter_id,tuple)                                    else voter_id
        voter_id2               = voter_id2[0]                 if isinstance(voter_id2,tuple)                                   else voter_id2
        business_department_id  = business_department_id[0]    if isinstance(business_department_id,tuple)                      else business_department_id
        stocker_id              = stocker_id[0]                if isinstance(stocker_id,tuple)                                  else stocker_id
        unit_heads_id           = unit_heads_id[0]             if isinstance(unit_heads_id,tuple)                               else unit_heads_id
        chief_acc_id            = chief_acc_id[0]              if isinstance(chief_acc_id,tuple)                                else chief_acc_id

        voter_id                = int(voter_id)                if voter_id               and voter_id != 'False'                else False
        voter_id2               = int(voter_id2)               if voter_id2              and voter_id2 != 'False'               else False
        business_department_id  = int(business_department_id)  if business_department_id and business_department_id != 'False'  else False
        stocker_id              = int(stocker_id)              if stocker_id             and stocker_id != 'False'              else False
        unit_heads_id           = int(unit_heads_id)           if unit_heads_id          and unit_heads_id != 'False'           else False
        chief_acc_id            = int(chief_acc_id)            if chief_acc_id           and chief_acc_id != 'False'            else False

        return voter_id,voter_id2,business_department_id,stocker_id,unit_heads_id,chief_acc_id

    @api.onchange('partner_id')
    def _onchange_partner_id_driver_consignee_id(self):
        voter_id, voter_id2, business_department_id, stocker_id, unit_heads_id, chief_acc_id = self.sudo()._get_id_sign()
        for rec in self.sudo():
            partner_id = rec.partner_id
            if partner_id and self.env.user.id == voter_id2:
                user = rec.env['res.users'].search(['|',('partner_id','=',partner_id.id),('name','ilike',partner_id.name)],limit=1)
                rec.driver_consignee_id = user
    
    @api.onchange('scheduled_date')
    def _onchange_scheduled_date(self):
        for rec in self.sudo():
            rec.scheduled_date = rec.scheduled_date

    @api.onchange('purchase_id', 'sale_id')
    def _onchange_source_document_sync_signatures(self):
        for rec in self:
            if hasattr(rec, 'purchase_id') and rec.purchase_id:
                history_ids = rec.purchase_id.purchase_sign_requests_history_ids.filtered(lambda x: x.approve_user_id)
                if history_ids:
                    rec.unit_heads_id = history_ids[-1].approve_user_id.id
            elif hasattr(rec, 'sale_id') and rec.sale_id:
                history_ids = rec.sale_id.sale_sign_requests_history_ids.filtered(lambda x: x.approve_user_id)
                if history_ids:
                    rec.unit_heads_id = history_ids[-1].approve_user_id.id

    @api.model
    def create(self, values):
        picking = super(StockPicking, self).create(values)

        voter_id, voter_id2, business_department_id, stocker_id, unit_heads_id, chief_acc_id = self.sudo()._get_id_sign()
        
        # Tự động lấy Thủ trưởng đơn vị từ PO/SO (ghi đè giá trị mặc định)
        if picking.purchase_id:
            history_ids = picking.purchase_id.purchase_sign_requests_history_ids.filtered(lambda x: x.approve_user_id)
            if history_ids:
                unit_heads_id = history_ids[-1].approve_user_id.id
            if picking.purchase_id.description and not values.get('reason_output_input_stock'):
                picking.reason_output_input_stock = picking.purchase_id.description
        elif picking.sale_id:
            history_ids = picking.sale_id.sale_sign_requests_history_ids.filtered(lambda x: x.approve_user_id)
            if history_ids:
                unit_heads_id = history_ids[-1].approve_user_id.id
        
        picking.write({
            'voter_id': picking.voter_id.id or self.env.user.id,
            'business_department_id': picking.business_department_id.id or business_department_id,
            'stocker_id': picking.stocker_id.id or stocker_id,
            'unit_heads_id': picking.unit_heads_id.id or unit_heads_id,
            'chief_acc_id': picking.chief_acc_id.id or chief_acc_id,
        })

        for rec in self.sudo():
            if rec.sale_id:
                rec.business_department_id = rec.sale_id.sales_team_captain_id.id

        # Auto-link moves to purchase order lines
        purchase = getattr(picking, 'purchase_id', False) or getattr(picking, 'purchase_order_id', False)
        if purchase:
            for move in picking.move_ids:
                if not move.purchase_line_id:
                    po_line = purchase.order_line.filtered(lambda l: l.product_id == move.product_id)
                    if po_line:
                        move.write({'purchase_line_id': po_line[0].id})

        return picking

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        if any(k in vals for k in ('purchase_id', 'purchase_order_id', 'move_ids', 'move_ids_without_package')):
            for picking in self:
                purchase = getattr(picking, 'purchase_id', False) or getattr(picking, 'purchase_order_id', False)
                if purchase:
                    for move in picking.move_ids:
                        if not move.purchase_line_id:
                            po_line = purchase.order_line.filtered(lambda l: l.product_id == move.product_id)
                            if po_line:
                                move.write({'purchase_line_id': po_line[0].id})
        return res

    def button_validate(self):
        for picking in self:
            # Bước 0: Xác nhận draft trước khi xử lý
            if picking.state == 'draft':
                picking.action_confirm()

            # Bước 1: Kiểm tra tình trạng còn hàng (action_assign) nếu chưa assign
            if picking.state in ('confirmed', 'waiting', 'partially_available'):
                picking.action_assign()
            # Bước 2: Thiết lập số lượng theo reservation
            if picking.state == 'assigned':
                for move in picking.move_ids:
                    for move_line in move.move_line_ids:
                        if not move_line.qty_done:
                            move_line.qty_done = move_line.reserved_uom_qty
        res = super(StockPicking, self).button_validate()

        # Bước 3: Tự động tạo hóa đơn điện tử (S-Invoice) cho các invoice đã posted
        for picking in self:
            if picking.state == 'done' and picking.sale_id:
                _logger.info("Picking %s đã done, kiểm tra invoice của sale order %s", picking.name, picking.sale_id.name)
                invoices = picking.sale_id.invoice_ids.filtered(
                    lambda m: m.state == 'posted'
                    and m.move_type == 'out_invoice'
                    and (m.sinvoice_count == 0 if hasattr(m, 'sinvoice_count') else True)
                )
                _logger.info("Tìm thấy %d invoice cần tạo S-Invoice", len(invoices))
                for inv in invoices:
                    try:
                        _logger.info("Đang tạo S-Invoice cho invoice %s", inv.name)
                        inv.sudo().action_create_data_sinvoice()
                        _logger.info("Đã tạo S-Invoice thành công cho invoice %s", inv.name)
                    except Exception as e:
                        _logger.error("Không thể tạo S-Invoice cho %s: %s", inv.name, e, exc_info=True)
        return res

    def action_create_picking_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Tạo phiếu kho",
            'res_model': 'create.picking.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_picking_type_id': 277,
            },
        }
