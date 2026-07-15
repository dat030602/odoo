from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
import logging
from odoo import SUPERUSER_ID

_logger = logging.getLogger(__name__)


class ccv_sale_plan_export(models.Model):
    _name = 'ccv.sale.plan.export'
    _order = 'date desc,state'

    name = fields.Char('Tên')
    team_id = fields.Many2one('crm.team', string="Đội bán hàng")
    type = fields.Selection(string="Loại", selection=[
        ('team','Khu vực'),
        ('summary','Tổng hợp'),
    ], default="team")
    state = fields.Selection(string="Trạng thái", selection=[
        ('draft','Nháp'),
        ('confirm','Xác nhận'),
        ('locked','Khóa'),
    ], default="draft")
    date = fields.Date(string="Ngày")

    is_next_plan = fields.Boolean(default=False, string="Kế hoạch dự kiến?")
    order_ids = fields.Many2many('sale.order',string='Đơn bán hàng')
    order_line_ids = fields.Many2many('sale.order.line',string='Dòng bán hàng')
    line_ids = fields.One2many('ccv.sale.plan.export.line','plan_export_id',string='Dòng kế hoạch')

    channel_id = fields.Many2one('mail.channel', string="Kênh bán hàng")

    @api.onchange('order_ids')
    def _onchange_order_ids(self):
        if self.state == 'locked':
            return

        if self.state in ['draft', 'confirm']:
            valid_order_lines = self.order_ids.mapped('order_line')
            removed_order_lines = self.order_line_ids - valid_order_lines
            if removed_order_lines:
                self.order_line_ids = [(3, line.id) for line in removed_order_lines]

    @api.onchange('order_line_ids')
    def _onchange_order_line_ids(self):
        for rec in self.sudo():
            if rec.state != 'confirm':
                continue

            if not rec.order_line_ids:
                if rec.line_ids:
                    rec.line_ids = [(5, 0, 0)]
                continue
            order_lines = rec.line_ids.filtered(lambda l:l.line_id).mapped('line_id')
            order_line_ids = rec.order_line_ids

            lines_to_remove = [idd for idd in order_lines._origin.ids if idd not in order_line_ids._origin.ids]
            if lines_to_remove:
                rec.line_ids = [(3, line_id._origin.id) for line_id in rec.line_ids.filtered(lambda l:l.line_id._origin.id in lines_to_remove)]

            # Tạo mới line_ids cho order_line_ids chưa có
            existing_line_order_line_ids = rec.line_ids.mapped('line_id')._origin.ids
            new_order_lines = rec.order_line_ids.filtered(lambda l: l._origin.id not in existing_line_order_line_ids)
            vals = []
            for line in new_order_lines:
                if line.product_uom_qty <= line.qty_delivered:
                    continue
                val = rec._prepare_plan_line(line)
                val.update({'plan_export_id': rec.id})
                vals.append(val)

            if vals:
                rec.line_ids.create(vals)

    def unlink(self):
        for rec in self:
            if rec.state == 'locked':
                raise UserError("Không thể xóa bản ghi khi đang ở trạng thái Khóa.")
        return super().unlink()

    @api.model
    def default_get(self, fields_list):
        defaults = super(ccv_sale_plan_export, self).default_get(fields_list)

        if self.type == 'team':
            team_id = self.env['crm.team'].search([
                '|', '|',
                ('user_id','=',self.env.user.id),
                ('member_ids','in',[self.env.user.id]),
                ('sales_assistant_ids','in',[self.env.user.id]),
            ], limit=1)
        else:
            team_id = False
        defaults['channel_id'] = self.env['mail.channel'].sudo().search([('id','=',811)], limit=1).id
        defaults['team_id'] = team_id
        defaults['date'] = date.today()

        return defaults

    def action_view_tree(self):
        self.ensure_one()
        lines = self.line_ids.ids
        action = self.env['ir.actions.act_window']._for_xml_id('ccv_plan_mrp_sale.action_ccv_sale_plan_export_line_view_tree')
        action['domain'] = [('id','in',lines)]
        action['context'] = {'default_plan_export_id': self.id}
        return action

    is_locked = fields.Boolean(default=False)
    can_set_draft = fields.Boolean(default=False, compute="_compute_count_sale")
    can_set_comfirm = fields.Boolean(default=False, compute="_compute_count_sale")

    can_create_pk = fields.Boolean(compute="_compute_count_sale")
    plan_pk_count = fields.Integer("Số lượng điều chuyển", compute="_compute_count_sale")
    plan_sale_count = fields.Integer("Số lượng kế hoạch", compute="_compute_count_sale")
    @api.depends("date")
    def _compute_count_sale(self):
        for rec in self:
            domain = [('type','=','team'),('date','=',rec.date)]
            if rec.type == 'team':
                domain = [('type','=','summary'),('date','=',rec.date)]
            rec.plan_sale_count = self.env['ccv.sale.plan.export'].search_count(domain)
            domain = [('plan_sale_id','!=',False),('plan_sale_id','=',rec.id)]
            if rec.type == 'team':
                summary_id = self.env['ccv.sale.plan.export'].search([('type','=','summary'),('date','=',rec.date)],limit=1)
                domain = [('plan_sale_id','!=',False),('plan_sale_id','=',summary_id.id),('sale_id.team_id.id','=',rec.team_id.id)]
            rec.plan_pk_count = self.env['stock.picking'].sudo().search_count(domain)
            rec.plan_mrp_count = self.env['ccv.mrp.plan.export'].search_count([('date','=',rec.date)])
            can_set_draft = False
            can_set_comfirm = False
            user = self.env.user

            if rec.state == 'locked':
                can_set_draft = True
                can_set_comfirm = True
                if rec.is_locked and not user.has_group('mrp.group_mrp_manager'):
                    can_set_draft = False
                    can_set_comfirm = False
            elif rec.state == 'confirm':
                can_set_draft = True
                can_set_comfirm = False
                if rec.is_locked and not user.has_group('mrp.group_mrp_manager'):
                    can_set_draft = False
                    can_set_comfirm = False

            rec.can_set_draft = can_set_draft
            rec.can_set_comfirm = can_set_comfirm
            if rec.plan_pk_count == 0 and rec.state == 'locked':
                rec.can_create_pk = True
            else:
                rec.can_create_pk = False

    def action_create_picking(self):
        for rec in self.sudo():
            lines = rec.line_ids
            orders = lines.mapped('order_id')
            for order in orders:
                vehicle_line_id = self.env['sale.vehicle.in.out.line'].search([('sale_order_ids','in',order.ids),('is_next_day','=',True),('next_day','=',rec.date)])
                if vehicle_line_id:
                    picking = order.picking_ids.filtered(lambda p: p.state not in ('done','cancel'))
                    picking.action_reset_to_draft()
                    picking.write({"plan_sale_id": rec.id, "stock_date_receipt": rec.date})
                    continue
                if order.state == 'draft':
                    order.sudo().with_context(plan_sale_id=rec.id,date=rec.date).action_confirm()
                order_lines = rec.line_ids.filtered(lambda l:l.order_id == order)
                for line in order_lines:
                    if line.line_id.product_uom_qty > 0:
                        line.line_id.write({'qty_to_export': line.qty_delivery})
                order.write({'procurement_group_id': False})
                order.sudo().with_context(plan_sale_id=rec.id,date=rec.date).action_launch_stock_rule()
                self.env.cr.commit()

    def action_view_pk(self):
        self.ensure_one()
        domain = [('plan_sale_id','=',self.id)]
        if self.type == 'team':
            summary_id = self.env['ccv.sale.plan.export'].search([('type','=','summary'),('date','=',self.date)],limit=1)
            domain = [('plan_sale_id','=',summary_id.id),('sale_id.team_id.id','=',self.team_id.id)]
        lines = self.env['stock.picking'].sudo().search(domain)
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        if len(lines) > 1:
            action['domain'] = [('id', 'in', lines.ids)]
        elif len(lines) == 1:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = lines.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_view_team_plan(self):
        self.ensure_one()
        domain = [('type','=','team'),('date','=',self.date)]
        action_view = "ccv_plan_mrp_sale.ccv_sale_plan_export_action_view_team"
        form_view = "ccv_plan_mrp_sale.ccv_sale_plan_export_form"
        if self.type == 'team':
            action_view = "ccv_plan_mrp_sale.ccv_sale_plan_export_action_view_summary"
            form_view = "ccv_plan_mrp_sale.ccv_sale_plan_export_form_sumary"
            domain = [('type','=','summary'),('date','=',self.date)]
        lines = self.env['ccv.sale.plan.export'].search(domain)
        action = self.env['ir.actions.act_window']._for_xml_id(action_view)
        if len(lines) > 1:
            action['domain'] = [('id', 'in', lines.ids)]
        elif len(lines) == 1:
            form_view = [(self.env.ref(form_view).id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = lines.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    plan_mrp_count = fields.Integer("Số lượng kế hoạch", compute="_compute_count_sale")

    def action_view_mrp_plan(self):
        self.ensure_one()
        lines = self.env['ccv.mrp.plan.export'].search([('date','=',self.date)])
        action = self.env['ir.actions.act_window']._for_xml_id('ccv_plan_mrp_sale.ccv_sale_plan_export_action_view_mrp')
        if len(lines) > 1:
            action['domain'] = [('id', 'in', lines.ids)]
        elif len(lines) == 1:
            form_view = [(self.env.ref('ccv_plan_mrp_sale.ccv_mrp_plan_export_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = lines.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.onchange('date','team_id')
    def _onchage_name_field(self):
        for rec in self:
            name = ""
            if rec.team_id:
                name += rec.team_id.report_name if rec.team_id.report_name else ""
            if name:
                name += ' - '
            if rec.date:
                name += rec.date.strftime("%d/%m/%Y")
            rec.name = name

    def _prepare_plan_line(self, line):
        return {
            "date": line.order_id.date_order,
            "order_id": line.order_id.id,
            "partner_id": line.order_id.partner_id.id,
            "product_id": line.product_id.id,
            "name": line.name,
            "product_uom_id": line.product_uom.id,
            "product_uom_qty": line.product_uom_qty,
            "qty_delivery": line.product_uom_qty - line.qty_delivered,
            "qty_delivered": line.qty_delivered,
            "line_id": line._origin.id,
            "note": "",
            "team_id": line.order_id.team_id.id,
        }

    def _prepare_plan_line_summary(self, line):
        qty_available = line.product_id.with_context(location=8).qty_available
        qty_delivery = line.product_uom_qty - line.qty_delivered
        return {
            "date": line.date,
            "order_id": line.order_id.id,
            "partner_id": line.partner_id.id,
            "qty_available": line.product_id.with_context(location=8).qty_available,
            "product_id": line.product_id.id,
            "name": line.name,
            "product_uom_id": line.product_uom_id.id,
            "product_uom_qty": line.product_uom_qty,
            "qty_delivery": line.qty_delivery,
            "qty_delivered": line.qty_delivered,
            "qty_mrp": qty_delivery - qty_available if qty_delivery > qty_available else 0,
            "line_id": line.line_id.id,
            "note": line.note,
            "team_id": line.team_id.id,
        }

    def action_confirm(self):
        for rec in self.sudo():
            vals = []
            if rec.type == 'team':
                if not rec.order_line_ids:
                    raise UserError("Bạn chưa chọn sản phẩm !!!")
                if rec.line_ids:
                    rec.line_ids.unlink()
                for line in rec.order_line_ids:
                    if line.product_uom_qty <= line.qty_delivered:
                        continue
                    val = self._prepare_plan_line(line)
                    val.update({'plan_export_id': rec.id})
                    vals.append(val)
            else:
                if rec.line_ids:
                    rec.line_ids.unlink()
                lines = self.env['ccv.sale.plan.export'].search([('date','=',rec.date),('state','=','locked'),('type','=','team')]).mapped('line_ids')
                for line in lines:
                    if line.qty_delivery <= 0:
                        continue
                    val = self._prepare_plan_line_summary(line)
                    val.update({'plan_export_id': rec.id})
                    vals.append(val)
            rec.line_ids.create(vals)
            rec.state = 'confirm'

    def action_lock(self):
        for rec in self:
            rec.is_locked = True
            rec.state = 'locked'

    def action_change_state_confirm(self):
        for rec in self:
            if rec.state in ('locked'):
                rec.state = 'confirm'

    def action_change_state_draft(self):
        for rec in self:
            if rec.state in ('locked','confirm'):
                rec.state = 'draft'

    def action_reset_uom_qty(self):
        self.line_ids._onchange_line_id()

