# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.fields import Command
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
import logging
import re

_logger = logging.getLogger(__name__)

class DetailsStockOrderBook(models.Model):
    _name = 'details.stock.order.book'
    _description = 'Báo cáo hàng tồn kho khu vực'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _order = 'id desc'

    name = fields.Char(string='Tên')
    warehouse_ids = fields.Many2many("stock.warehouse", string="Kho")
    voter_id = fields.Many2one('res.users', string="Người lập")
    team_sale_id = fields.Many2one('res.users', string="Trưởng khu vực")
    chief_finance_id = fields.Many2one('res.users', string="Phòng Kế toán")
    lead_sale_id = fields.Many2one('res.users', string="Phòng Kinh doanh")
    director_id = fields.Many2one('res.users', string="Thủ trưởng đơn vị")
    active = fields.Boolean(default=True)
    team_id = fields.Many2one("crm.team", string="Đội bán hàng")
    
    line_ids = fields.One2many('details.stock.order.book.line', 'parent_id', string="Chi tiết", readonly=True)
    
    state = fields.Selection(
        [('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'), ('refuse', 'Từ chối'), ('cancel', 'Hủy')],
        'Trạng thái', default='draft', tracking=True)

    trp_approve_history_ids = fields.One2many('trp.approve.history', 'details_stock_order_book_id', string='Lịch sử duyệt', copy=False)

    def unlink(self):
        for record in self:
            if record.state not in ['refuse', 'cancel', 'draft']:
                raise UserError("Không thể xóa yêu cầu ký đã duyệt!")
        return super(DetailsStockOrderBook, self).unlink()

    def action_cancel(self):
        self.write({'state': 'cancel'})
        res_history = self.trp_approve_history_ids
        self.env['mail.activity'].search([('trp_approve_history_id', 'in', res_history.ids)]).with_context(skip_approve_done=True).action_done()

    def action_undo(self):
        self.write({'state': 'draft'})

    @api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.manager_type',
                 'trp_approve_config_line_id.user_ids', 'trp_approve_config_line_id.job_ids',
                 'team_sale_id', 'lead_sale_id', 'chief_finance_id', 'voter_id')
    def _compute_current_approve_users(self):
        super(DetailsStockOrderBook, self)._compute_current_approve_users()
        for record in self:
            cfg = record.trp_approve_config_line_id
            if cfg:
                approver_ids = record.current_approve_user_ids.ids
                if cfg.manager_type == 'team_sale':
                    if record.team_sale_id:
                        approver_ids.append(record.team_sale_id.id)
                elif cfg.manager_type == 'commercial_department':
                    if record.lead_sale_id:
                        approver_ids.append(record.lead_sale_id.id)
                elif cfg.manager_type == 'creator':
                    if record.voter_id:
                        approver_ids.append(record.voter_id.id)
                
                record.current_approve_user_ids = [(6, 0, list(set(approver_ids)))]

    def action_sign(self):
        self = self.sudo()
        if not self.line_ids:
            raise ValidationError("Vui lòng lấy dữ liệu trước khi trình duyệt!")
        res_approve = {}
        if not self.trp_approve_config_line_id and self.state in ('draft'):
            self.approve_next_action = 'action_sign'
            self.approve_state_init = self.state
            self.approve_state_next = 'approve'
            res_approve = self.with_context(approve_type='new').create_approve()
        if not res_approve or not self.trp_approve_config_line_id:
            if self.state == 'approve':
                self.update({'state': 'approved'})
                return

    def action_agree(self):
        res = super(DetailsStockOrderBook, self).action_agree()
        for record in self:
            if record.state == 'approved':
                record.message_post(
                    body=f"Báo cáo hàng tồn kho khu vực {record._get_html_link()} đã được duyệt.",
                )
        return res

    def action_print_excel(self):
        # We can implement an excel export if a report_action exists, otherwise fallback to the old way
        # Since this refers to `ccv_report_stock_order.stock_order_report` we can try to call it
        return self.env.ref('ccv_report_stock_order.stock_order_report').report_action(self)

    def action_print_pdf(self):
        return self.env.ref('biz_details_purchase_report.action_details_stock_order_book_pdf').report_action(self)

    def action_print_excel(self):
        return self.env.ref('biz_details_purchase_report.action_details_stock_order_book_xlsx').report_action(self)

    @api.model
    def default_get(self, fields_list):
        defaults = super(DetailsStockOrderBook, self).default_get(fields_list)

        env_params = self.env['ir.config_parameter'].sudo()
        
        # Chỉ lấy tham số cấu hình riêng cho báo cáo này
        stock_team_sale_id = env_params.get_param('biz_details_purchase_report.stock_team_sale_id', False)
        stock_lead_sale_id = env_params.get_param('biz_details_purchase_report.stock_lead_sale_id', False)
        stock_chief_finance_id = env_params.get_param('biz_details_purchase_report.stock_chief_finance_id', False)
        director_id = env_params.get_param('biz_details_purchase_report.director_id', False)
        
        defaults.update({
            'name': f'Báo cáo hàng tồn kho khu vực ngày {date.today().strftime("%d-%m-%Y")}',
            'voter_id': self.env.user.id,
            'chief_finance_id': int(stock_chief_finance_id) if (stock_chief_finance_id and stock_chief_finance_id != '0') else False,
            'lead_sale_id': int(stock_lead_sale_id) if (stock_lead_sale_id and stock_lead_sale_id != '0') else False,
            'director_id': int(director_id) if (director_id and director_id != '0') else False,
        })
        
        if stock_team_sale_id and stock_team_sale_id != '0':
            defaults['team_sale_id'] = int(stock_team_sale_id)
        else:
            # Nếu không cấu hình cố định, tự động tìm Team CRM của người dùng hiện tại
            team = self.env['crm.team'].sudo().search([
                '|', '|',
                ('user_id','=',self.sudo().env.user.id),
                ('member_ids','in',[self.sudo().env.user.id]),
                ('sales_assistant_ids','in',[self.sudo().env.user.id]),
            ], limit=1)
            
            if team:
                defaults.update({
                    'team_sale_id': team.user_id.id,
                    'team_id': team.id,
                })
        
        return defaults

    @api.onchange('team_id')
    def _onchange_team_id(self):
        for rec in self:
            rec.team_sale_id = rec.team_id.user_id

    def action_confirm(self):
        self.ensure_one()
        self.line_ids.unlink()
        data = self._get_product_inventory()
        if not data:
            return
        self.write({'line_ids': data})

    def _get_product_inventory(self):
        self.ensure_one()
        if not self.warehouse_ids:
            return []

        result = []
        stock_env = self.env

        location_ids = self.warehouse_ids.mapped('lot_stock_id').ids
        if not location_ids:
            return []

        quants = stock_env['stock.quant'].search([
            ('quantity', '>', 0),
            ('location_id', 'in', location_ids),
        ])

        product_stock = {}
        for quant in quants:
            product = quant.product_id
            if product not in product_stock:
                product_stock[product] = 0.0
            product_stock[product] += quant.quantity

        for product, total_stock in product_stock.items():
            allocated_stock = 0.0

            mrp_prods = stock_env['mrp.production'].search([
                ('product_id', '=', product.id),
                ('state', '=', 'done'),
            ])

            related_orders = mrp_prods.mapped('sale_ids').filtered(lambda l: l.state not in ('cancel', 'draft'))

            for order in related_orders.sorted(key=lambda r: r.date_order):
                if allocated_stock >= total_stock:
                    break

                lines = order.order_line.filtered(lambda l: l.product_id == product)
                qty_ordered = sum(lines.mapped('product_uom_qty'))
                qty_delivered = sum(lines.mapped('qty_delivered'))

                needed_quantity = qty_ordered - qty_delivered

                if needed_quantity > 0.01:
                    available_stock_to_allocate = total_stock - allocated_stock
                    actual_allocation = min(needed_quantity, available_stock_to_allocate)

                    if actual_allocation > 0:
                        order_mrps = mrp_prods.filtered(lambda m: order in m.sale_ids and m.stock_date_receipt)
                        order_mrps = sorted(order_mrps, key=lambda m: m.stock_date_receipt, reverse=True)

                        date_proc = order_mrps[0].stock_date_receipt.date() if order_mrps else None
                        picking_type_id = order_mrps[0].picking_type_id.id if order_mrps else False

                        if not self.team_id or order.team_id.id == self.team_id.id:
                            result.append(Command.create({
                                'name': f'Phân bổ cho SO {order.name}',
                                'product_id': product.id,
                                'order_id': order.id,
                                'partner_id': order.partner_id.id,
                                'team_id': order.team_id.id,
                                'quantity': actual_allocation,
                                'date_proc': date_proc,
                                'picking_type_id': picking_type_id,
                                'note': f'Đơn hàng cần {needed_quantity:.2f}, phân bổ {actual_allocation:.2f} từ tồn kho',
                            }))
                        allocated_stock += actual_allocation

            remaining_stock_for_reserve = total_stock - allocated_stock
            if remaining_stock_for_reserve > 0.01 and not self.team_id:
                latest_mrp_for_reserve = mrp_prods.filtered(lambda m: m.stock_date_receipt)
                latest_mrp_for_reserve = sorted(latest_mrp_for_reserve, key=lambda m: m.stock_date_receipt, reverse=True)

                date_proc = latest_mrp_for_reserve[0].stock_date_receipt.date() if latest_mrp_for_reserve else None
                picking_type_id = latest_mrp_for_reserve[0].picking_type_id.id if latest_mrp_for_reserve else False

                result.append(Command.create({
                    'name': f'Dự trữ {product.display_name}',
                    'product_id': product.id,
                    'quantity': remaining_stock_for_reserve,
                    'date_proc': date_proc,
                    'picking_type_id': picking_type_id,
                    'note': 'Hàng tồn kho chưa phân bổ',
                }))

        return result
