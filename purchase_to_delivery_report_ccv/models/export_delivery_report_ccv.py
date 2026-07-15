# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime

class ExportDeliveryReportCcv(models.Model):
    _name = 'export.delivery.report.ccv'
    _description = 'Báo cáo chốt lô nguyên liệu'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _order = 'id desc'

    name = fields.Char(string='Tên báo cáo', required=True, copy=False, default=lambda self: _('Báo cáo chốt lô nguyên liệu mới'))

    @api.onchange('purchase_id')
    def _onchange_purchase_id(self):
        if self.purchase_id:
            # Chỉ tự nhảy tên nếu tên đang trống hoặc đang là tên mặc định
            if not self.name or self.name == 'Báo cáo chốt lô nguyên liệu mới' or self.name.startswith('Báo cáo chốt lô nguyên liệu -'):
                self.name = 'Báo cáo chốt lô nguyên liệu - ' + self.purchase_id.name
    purchase_id = fields.Many2one('purchase.order', string='Đơn mua hàng', required=True)
    delivery_picking_ids = fields.Many2many(
        'stock.picking',
        string='Delivery Orders to Export'
    )

    product_names = fields.Char(string='Sản phẩm', compute='_compute_product_info')
    supplier_name = fields.Char(string='Nhà cung cấp', related='purchase_id.partner_id.name', store=True)
    bag_weights = fields.Char(string='Trọng lượng bao', compute='_compute_product_info')
    tare_weights = fields.Char(string='Định mức bao bì', compute='_compute_product_info')
    total_qty = fields.Float(string='Số lượng (Tấn)', compute='_compute_product_info')
    contract_number = fields.Char(string='Số hợp đồng', related='purchase_id.partner_ref')
    customs_number = fields.Char(string='Số tờ khai hải quan', related='purchase_id.custom_declaration_number')
    customs_date = fields.Date(string='Ngày tờ khai', related='purchase_id.custom_declaration_date')

    @api.depends('purchase_id', 'purchase_id.order_line', 'purchase_id.order_line.product_id', 'purchase_id.order_line.product_uom_qty')
    def _compute_product_info(self):
        for record in self:
            if record.purchase_id:
                po = record.purchase_id
                products = po.order_line.mapped('product_id.name')
                bag_ws = po.order_line.mapped('product_id.default_specification_id.name')
                tare_ws = po.order_line.mapped('product_id.packaging_specification_id.name')

                record.product_names = '\n'.join(filter(None, products)) if products else ''
                record.bag_weights = '\n'.join(filter(None, bag_ws)) if bag_ws else ''
                record.tare_weights = '\n'.join(filter(None, tare_ws)) if tare_ws else ''
                record.total_qty = sum(po.order_line.mapped('product_uom_qty'))
            else:
                record.product_names = ''
                record.bag_weights = ''
                record.tare_weights = ''
                record.total_qty = 0.0

    voter_id = fields.Many2one('res.users', string='Người Lập Phiếu')
    accounting_department_id = fields.Many2one('res.users', string='Phòng kế toán')
    factory_ids = fields.Many2many(
        'res.users', 
        relation='export_delivery_report_ccv_factory_rel', 
        column1='report_id', 
        column2='user_id', 
        string='Nhà máy'
    )
    chief_accountant_id = fields.Many2one('res.users', string='Kế Toán Trưởng')
    trade_department_id = fields.Many2one('res.users', string='Trưởng Phòng Thương mại')
    unit_heads_id = fields.Many2one(
        'res.users', string='Thủ trưởng đơn vị',
        compute='_compute_unit_heads_id', store=True, readonly=False
    )

    state = fields.Selection(
        [('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'), ('refuse', 'Từ chối'), ('cancel', 'Hủy')],
        string='Trạng thái', default='draft', tracking=True)

    trp_approve_history_ids = fields.One2many('trp.approve.history', 'export_delivery_report_id', string='Lịch sử duyệt', copy=False)

    @api.depends('trp_approve_history_ids', 'trp_approve_history_ids.approve_user_id',
                 'trp_approve_history_ids.trp_approve_config_line_id')
    def _compute_unit_heads_id(self):
        for rec in self:
            default_user_id = self.env['ir.config_parameter'].sudo().get_param(
                'purchase_to_delivery_report_ccv.unit_heads_id'
            )
            try:
                default_user_id = int(default_user_id) if default_user_id else False
            except ValueError:
                default_user_id = False

            histories_with_level = rec.trp_approve_history_ids.filtered(
                lambda h: h.trp_approve_config_line_id and h.trp_approve_config_line_id.level
            )
            if histories_with_level:
                max_level = max(histories_with_level.mapped('trp_approve_config_line_id.level'))
                last_level_history = histories_with_level.filtered(
                    lambda h: h.trp_approve_config_line_id.level == max_level and h.approve_user_id
                )
                if last_level_history:
                    rec.unit_heads_id = last_level_history[0].approve_user_id
                else:
                    if not rec.unit_heads_id:
                        rec.unit_heads_id = default_user_id
            else:
                if not rec.unit_heads_id:
                    rec.unit_heads_id = default_user_id

    # Map từ manager_type → field chứa res.users trên record này
    _MANAGER_TYPE_FIELD_MAP = {
        'voter': 'voter_id',
        'accounting_department': 'accounting_department_id',
        'factory': 'factory_ids',
        'chief_accountant': 'chief_accountant_id',
        'trade_department': 'trade_department_id',
        'unit_heads': 'unit_heads_id',
    }

    def _compute_current_approve_users(self):
        for record in self:
            list_approver = []
            line = record.trp_approve_config_line_id
            if line:
                if line.user_ids:
                    list_approver = list(line.user_ids.ids)

                for job_line in line.job_ids:
                    list_approver += job_line.employee_ids.ids

                if line.manager_type:
                    # Xử lý các manager_type tùy chỉnh của module này
                    field_name = record._MANAGER_TYPE_FIELD_MAP.get(line.manager_type)
                    if field_name and hasattr(record, field_name):
                        users = getattr(record, field_name)
                        if users:
                            # Xử lý cho cả Many2one và Many2many
                            user_ids = users.ids if hasattr(users, 'ids') else [users.id]
                            for uid in user_ids:
                                if uid not in list_approver:
                                    list_approver.append(uid)
                    elif line.manager_type == 'manager':
                        user_manager = record.create_uid.department_id.manager_id.user_id.id
                        if user_manager and user_manager not in list_approver:
                            list_approver.append(user_manager)
                    elif line.manager_type == 'parent':
                        user_parent = record.create_uid.employee_id.parent_id.user_id.id
                        if user_parent and user_parent not in list_approver:
                            list_approver.append(user_parent)
                    elif line.manager_type == 'delegate':
                        approved_user_ids = record.trp_approve_history_ids.mapped('approve_user_id')
                        list_approver += (record.delegate_approver_ids - approved_user_ids).ids

                if len(record.delegate_approver_ids) > 0:
                    list_approver += record.delegate_approver_ids.ids

                record.current_approve_user_ids = [(6, 0, list(set(list_approver)))]
            else:
                record.current_approve_user_ids = False

    def default_get(self, fields_list):
        res = super(ExportDeliveryReportCcv, self).default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()
        
        if 'voter_id' in fields_list:
            res['voter_id'] = self.env.user.id
            
        param_mapping = {
            'accounting_department_id': 'purchase_to_delivery_report_ccv.accounting_department_id',
            'factory_id': 'purchase_to_delivery_report_ccv.factory_id',
            'chief_accountant_id': 'purchase_to_delivery_report_ccv.chief_accountant_id',
            'trade_department_id': 'purchase_to_delivery_report_ccv.trade_department_id',
            'unit_heads_id': 'purchase_to_delivery_report_ccv.unit_heads_id'
        }
        
        for field, param in param_mapping.items():
            if field in fields_list:
                val = env_params.get_param(param, False)
                res[field] = int(val) if val and str(val).isdigit() else False
                
        return res

    def action_confirm(self):
        """Lấy dữ liệu (Populate picking_ids based on purchase_id)"""
        for record in self:
            if not record.purchase_id:
                raise ValidationError(_("Vui lòng chọn Đơn mua hàng!"))
            record.delivery_picking_ids = [(5, 0, 0)]
            pickings = record.purchase_id.stock_input_ids.mapped('picking_id')
            if pickings:
                record.delivery_picking_ids = [(6, 0, pickings.ids)]
            else:
                raise ValidationError(_("Không tìm thấy lệnh chuyển hàng (stock.picking) nào liên quan tới đơn mua hàng này!"))

    def action_sign(self):
        self = self.sudo()
        if not self.delivery_picking_ids:
            raise ValidationError("Vui lòng Lấy dữ liệu trước khi trình duyệt!")
        res_approve = {}
        if not self.trp_approve_config_line_id and self.state == 'draft':
            self.approve_next_action = 'action_sign'
            self.approve_state_init = self.state
            self.approve_state_next = 'approve'
            res_approve = self.with_context(approve_type='new').create_approve()
        if not res_approve or not self.trp_approve_config_line_id:
            if self.state == 'approve':
                self.update({'state': 'approved'})

    def action_cancel(self):
        self.write({'state': 'cancel'})
        res_history = self.trp_approve_history_ids
        self.env['mail.activity'].search([('trp_approve_history_id', 'in', res_history.ids)]).with_context(skip_approve_done=True).action_done()

    def action_undo(self):
        self.write({'state': 'draft'})

    def _get_approvers_for_line(self, line):
        self.ensure_one()
        list_approver = []
        if line.user_ids:
            list_approver = line.user_ids.ids

        if line.manager_type:
            field_map = {
                'voter': 'voter_id',
                'accounting_department': 'accounting_department_id',
                'factory': 'factory_ids',
                'chief_accountant': 'chief_accountant_id',
                'trade_department': 'trade_department_id',
                'unit_heads': 'unit_heads_id',
            }
            field_name = field_map.get(line.manager_type)
            if field_name and hasattr(self, field_name):
                users = getattr(self, field_name)
                if users:
                    # Xử lý cho cả Many2one và Many2many
                    user_ids = users.ids if hasattr(users, 'ids') else [users.id]
                    for uid in user_ids:
                        if uid not in list_approver:
                            list_approver.append(uid)
        return list_approver

    def action_print_excel(self):
        self.ensure_one()
        return self.env.ref('purchase_to_delivery_report_ccv.action_import_report_ccv_xlsx').report_action(self)

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref('purchase_to_delivery_report_ccv.action_import_report_ccv_pdf').report_action(self)

    def unlink(self):
        for record in self:
            if record.state not in ['refuse', 'cancel', 'draft']:
                raise UserError("Không thể xóa báo cáo đã duyệt hoặc đang duyệt!")
        return super(ExportDeliveryReportCcv, self).unlink()
