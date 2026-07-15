from odoo import api, fields, models, tools, _
import logging

_logger = logging.getLogger(__name__)

class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    has_picking = fields.Selection(string="Tạo phiếu kho",selection=[
        ('required','Bắt buộc'),
        ('no','Không'),
    ],default="no")
    has_rent = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Thuê xe', default='no')
    has_partner_in_product = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Chọn liên hệ trong sản phẩm', default='no')

    has_image_in_product = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Hình ảnh trong sản phẩm', default='no')
    has_line_image = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Hình ảnh', default='no')
    has_note_in_product = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Ghi chú trong sản phẩm', default='no')
    has_mkt_comment = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Ý kiến MKT', default='no')
    has_stock_in_product = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Tồn kho trong sản phẩm', default='no')
    has_service_in_product = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Dịch vụ trong sản phẩm', default='no')
    has_qty_income_in_product = fields.Selection(selection=[
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='SL nhập trong sản phẩm', default='no')
    has_qty_outcome_in_product = fields.Selection(selection=[
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='SL xuất trong sản phẩm', default='no')
    
    has_picking_type = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Chọn loại hoạt động', default='no')

    has_warehouse = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Chọn kho', default='no')
    

    has_team_id = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Chọn đội ngũ kinh doanh', default='no')
    has_department_id = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Chọn phòng ban', default='no')
    has_sale_ids = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Chọn đơn bán hàng', default='no')

    has_reason = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Hiển thị lý do', default='no')

    has_count_production = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Hiển thị số lần sản xuất', default='no')

    has_count_stock = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Hiển thị số lần tồn kho', default='no')

    has_qty_produced = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Hiển thị số lượng sản xuất', default='no')
    has_qty_bb_used = fields.Selection(selection=[
        ('required', 'Bắt buộc'),
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Số lượng BB đã sử dụng', default='no')
    
    has_create_daily_work_output_other = fields.Selection(selection=[
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Hiển thị nút đẩy lương', default='no')
    has_purchase = fields.Selection(selection=[
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Xem đơn mua hàng', default='no')

    @api.onchange('has_product')
    def _onchange_has_product(self):
        for rec in self:
            if rec.has_product == 'no':
                rec.has_partner_in_product = 'no'

    def action_to_review_category(self):
        approver = self.env['approval.approver'].search([
            ('user_id', '=', self.env.user.id),
            ('status', '=', 'pending'),
            ('request_id.request_status', '=', 'pending'),
            ('request_id.category_id', '=', self.id),
        ])
        return {
            'name': 'Phê duyệt cần xem xét',
            'res_model': 'approval.request',
            'view_mode': 'tree,form,kanban',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'domain' : [('id','in', approver.mapped('request_id').ids)]
        }

    def _compute_request_to_validate_count(self):
        for category in self:
            category_count = self.env['approval.approver'].search([
                ('user_id', '=', self.env.user.id),
                ('status', '=', 'pending'),
                ('request_id.request_status', '=', 'pending'),
                ('request_id.category_id', '=', category.id),
            ])
            category.request_to_validate_count = len(category_count)
