from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
import logging
from collections import defaultdict

_logger = logging.getLogger(__name__)


class ccv_mrp_plan_export(models.Model):
    _name = 'ccv.mrp.plan.export'
    _order = 'date desc'

    name = fields.Char('Tên')
    state = fields.Selection(string="Trạng thái", selection=[
        ('draft','Nháp'),
        ('confirm','Xác nhận'),
        ('locked','Khóa'),
    ], default="draft")
    date = fields.Date(string="Ngày")
    location_id = fields.Many2one("stock.location",string="Kho hàng")
    location_ids = fields.Many2many("stock.location",string="Kho hàng")
    line_ids = fields.One2many('ccv.sale.plan.export.line2','plan_export_id',string='Dòng kế hoạch')
    @api.onchange('date')
    def _onchage_name_field(self):
        for rec in self:
            name = "KẾ HOẠCH SẢN XUẤT "
            if rec.date:
                name += rec.date.strftime("%d/%m/%Y")
            rec.name = name

    def _prepare_plan_line(self, lines,product_id):
        if not lines:
            return False
        boms_by_product = self.env['mrp.bom'].with_context(active_test=True)._bom_find(product_id, company_id=1, bom_type='normal')
        bom = boms_by_product[product_id]
        data = {
            "is_promotional_product": any([line.line_id.is_promotional_product for line in lines if line.line_id.is_promotional_product]),
            "product_id": product_id.id,
            "qty_delivery": sum(lines.mapped('qty_delivery')),
            "bom_id": bom.id or False,
            "note": "\n".join(line.note if line.note else "" for line in lines),
        }
        factory_default_ids = self.env['factory.product.default'].search([])
        for factory_default_id in factory_default_ids:
            cur_fac_pro = factory_default_id._get_factory_product(product_id)
            if cur_fac_pro:
                data.update({'picking_type_id': cur_fac_pro.picking_type_id.id})
                break
        return data
    
    def action_reset_description(self):
        for rec in self:
            sale_lines = self.env['ccv.sale.plan.export'].search([('date','=',rec.date),('state','=','locked'),('type','=','summary')]).mapped('line_ids')
            for line in rec.line_ids.sudo():
                cur_sales = sale_lines.filtered(lambda l:l.product_id == line.product_id)
                qty_available_total = line.qty_available
                description = []

                for cur_sale in cur_sales:
                    if qty_available_total < 0:
                        qty_available_total = 0
                    qty_delivery = cur_sale.qty_delivery if cur_sale.qty_delivery > 0 else 0
                    cur_qty_mrp = qty_delivery - qty_available_total if qty_delivery > qty_available_total else 0
                    qty_need = cur_qty_mrp if cur_qty_mrp > 0 else 0
                    description.append("-".join([
                        cur_sale.partner_id.name if cur_sale.partner_id else "",cur_sale.order_id.name if cur_sale.order_id else "",
                        "%s %s" % (str(round(qty_need,3)), cur_sale.product_uom_id.name if cur_sale.product_uom_id else ""),
                        cur_sale.team_id.code if cur_sale.team_id.code else "",
                        cur_sale.note if cur_sale.note else ""
                    ]))
                    qty_available_total -= cur_sale.qty_delivery
                line.description = '\n'.join(description)

    @api.model
    def default_get(self, fields_list):
        defaults = super(ccv_mrp_plan_export, self).default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()
        location_id = int(env_params.get_param('ccv_plan_mrp_sale.location_id', 0))
        if location_id:
            defaults.update({
                'date': date.today(),
                'location_id': location_id,
                'location_ids': [(4,location_id)],
            })
        return defaults

    def action_view_tree(self):
        self.ensure_one()
        lines = self.line_ids.ids
        action = self.env['ir.actions.act_window']._for_xml_id('ccv_plan_mrp_sale.action_ccv_sale_plan_export_line2_view_tree')
        action['domain'] = [('id','in',lines)]
        action['context'] = {'default_plan_export_id': self.id}
        return action
    
    plan_sale_count = fields.Integer("Số lượng kế hoạch", compute="_compute_count_sale")
    @api.depends("date")
    def _compute_count_sale(self):
        for rec in self:
            rec.plan_sale_count = self.env['ccv.sale.plan.export'].search_count([('type','=','summary'),('date','=',rec.date)])
            
    def action_view_summary(self):
        self.ensure_one()
        lines = self.env['ccv.sale.plan.export'].search([('type','=','summary'),('date','=',self.date)])
        action = self.env['ir.actions.act_window']._for_xml_id('ccv_plan_mrp_sale.ccv_sale_plan_export_action_view_summary')
        if len(lines) > 1:
            action['domain'] = [('id', 'in', lines.ids)]
        elif len(lines) == 1:
            form_view = [(self.env.ref('ccv_plan_mrp_sale.ccv_sale_plan_export_form_sumary').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = lines.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_confirm(self):
        for rec in self.sudo():
            vals = []
            if rec.line_ids:
                rec.line_ids.unlink()
            lines = self.env['ccv.sale.plan.export'].search([('date','=',rec.date),('state','=','locked'),('type','=','summary')]).mapped('line_ids')
            product_ids = lines.mapped('product_id')
            for product_id in product_ids:
                val = self._prepare_plan_line(lines.filtered(lambda l:l.product_id == product_id),product_id)
                val.update({'plan_export_id': rec.id})
                vals.append(val)
            rec.line_ids.create(vals)
            rec.line_ids._set_qty_delivery()
            rec.line_ids._onchange_qty_delivery()
            rec.action_reset_description()
            rec.state = 'confirm'

    def action_reset_qty(self):
        self.line_ids._set_qty_delivery()
        self.line_ids._onchange_qty_delivery()

    def action_lock(self):
        for rec in self:
            rec.state = 'locked'

    def action_change_state_confirm(self):
        for rec in self:
            if rec.state in ('locked'):
                rec.state = 'confirm'

    def action_change_state_draft(self):
        for rec in self:
            if rec.state in ('locked','confirm'):
                rec.state = 'draft'

    def action_create_mrp_order(self):
        vals = []
        for rec in self:
            for line in rec.line_ids.filtered(lambda l: l.bom_id):
                if line.qty_mrp > 0:
                    sale_lines = self.env['ccv.sale.plan.export'].search([('date','=',rec.date),('state','=','locked'),('type','=','summary')]).mapped('line_ids')
                    cur_sales = sale_lines.filtered(lambda l:l.product_id == line.product_id)
                    vals.append({
                        'product_id': line.product_id.id,
                        'bom_id': line.bom_id.id if line.bom_id else False,
                        'date_planned_start':rec.date,
                        'picking_type_id': line.picking_type_id.id,
                        'user_id': line.picking_type_id.user_id.id if line.picking_type_id.user_id else False,
                        'stock_date_receipt':rec.date,
                        'product_qty': line.qty_mrp,
                        'interpretation': line.description,
                        'origin': line.description,
                        'plan_mrp_id': rec.id,
                        'plan_mrp_line_id': line.id,
                        'sale_ids': [(4,sale_id.id) for sale_id in cur_sales.mapped('order_id')],
                        'partner_ids': [(4,partner_id.id) for partner_id in cur_sales.mapped('order_id').mapped('partner_id')],
                    })
        mrp_ids = self.env['mrp.production'].create(vals)
        for mrp_id in mrp_ids:
            body = "Lệnh sản xuất được tạo từ %s" % mrp_id.plan_mrp_id._get_html_link()
            mrp_id.message_post(body=body)
        return mrp_ids

    can_create_mo = fields.Boolean(compute="_compute_count_mo")
    plan_mo_count = fields.Integer("SL Lệnh sản xuất", compute="_compute_count_mo")

    @api.depends("date")
    def _compute_count_mo(self):
        for rec in self:
            rec.plan_mo_count = self.env['mrp.production'].sudo().search_count([('plan_mrp_id','=',self.id)])
            if rec.plan_mo_count == 0 and rec.state == 'locked':
                rec.can_create_mo = True
            else:
                rec.can_create_mo = False

    def action_view_mo(self):
        self.ensure_one()
        lines = self.env['mrp.production'].sudo().search([('plan_mrp_id','=',self.id)])
        action = self.env['ir.actions.act_window']._for_xml_id('mrp.mrp_production_action')
        if len(lines) > 1:
            action['domain'] = [('id', 'in', lines.ids)]
        elif len(lines) == 1:
            form_view = [(self.env.ref('mrp.mrp_production_form_view').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = lines.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
