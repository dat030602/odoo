from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree
import datetime
import logging

_logger = logging.getLogger(__name__)

class SaleVehicleInOut(models.Model):
    _name = 'sale.vehicle.in.out'
    _description = 'Vehicle In/Out'
    _order = 'date desc'
    
    name = fields.Char("Name", readonly=True)
    date = fields.Date(string="Date",required=True)
    ra_loa = fields.Boolean(string="Ra loa", default=False, tracking=True)
    line_ids = fields.One2many('sale.vehicle.in.out.line','sale_vehicle_id')

    is_warehouse_readonly = fields.Boolean(compute='_compute_is_warehouse_readonly')

    def _compute_is_warehouse_readonly(self):
        for rec in self:
            rec.is_warehouse_readonly = self.env.user.has_group('ccv_api_connector.group_vehicle_warehouse_readonly')

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        
        is_warehouse = self.env.user.has_group('ccv_api_connector.group_vehicle_warehouse_readonly')
        is_baove = self.env.user.has_group('ccv_api_connector.group_vehicle_security')
        is_main = self.env.user.has_group('ccv_api_connector.group_vehicle_main_action')
        is_invite = self.env.user.has_group('ccv_api_connector.group_vehicle_invite_only')
        is_complete = self.env.user.has_group('ccv_api_connector.group_vehicle_complete_only')
        is_out = self.env.user.has_group('ccv_api_connector.group_vehicle_out_confirm')
        is_admin = self.env.user.has_group('ccv_api_connector.group_admin')
        
        any_security = is_baove or is_main or is_invite or is_complete or is_out
        
        if True:
            doc = etree.XML(res['arch'])
            if view_type in ('form', 'tree'):
                if is_warehouse:
                    doc.set('create', '0')
                    doc.set('edit', '0')
                    doc.set('delete', '0')
                
                if view_type == 'form':
                    for field in doc.xpath("//field[@name='line_ids']"):
                        tree_nodes = field.xpath("tree")
                        if tree_nodes:
                            for tree in tree_nodes:
                                if is_out or is_admin:
                                    tree.set('delete', '1')
                                    # Create is allowed by default, so we don't set create=1
                                elif any_security:
                                    tree.set('create', '0')
                                    tree.set('delete', '0')
                                    if not (is_main or is_invite or is_complete):
                                        tree.set('edit', '0')
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    status = fields.Selection(string="Status", selection=[
        ('open', 'Open'),
        ('lock', 'Locked'),
    ],compute="_compute_status")
    
    type = fields.Selection(
        selection=[
            ('in', 'Nhập'),
            ('out', 'Xuất'),
        ],
        string="Loại",
        compute='_compute_type',
    )
    count_line_w_domain = fields.Integer(string="Số lượng phiếu", compute='_compute_type')
    
    other_type = fields.Selection(
        selection=[
            ('in', 'Nhập'),
            ('out', 'Xuất'),
        ],
        string="Loại khác",
        compute='_compute_other_type',
    )
    count_other_line_w_domain = fields.Integer(string="Số lượng khác", compute='_compute_other_type')

    @api.depends_context('type')
    @api.depends('line_ids')
    def _compute_other_type(self):
        for rec in self:
            current_type = self.env.context.get('type', 'out')
            rec.other_type = 'in' if current_type == 'out' else 'out'
            rec.count_other_line_w_domain = len(rec.line_ids.filtered(lambda l: l.type == rec.other_type))

    @api.depends_context('type')
    @api.depends('line_ids')
    def _compute_type(self):
        for rec in self:
            rec.type = self.env.context.get('type', 'out')
            rec.count_line_w_domain = len(rec.line_ids.filtered(lambda l:l.type == rec.type))
    
    @api.model
    def default_get(self, fields_list):
        defaults = super(SaleVehicleInOut, self).default_get(fields_list)
        defaults['date'] = fields.Date.context_today(self) + datetime.timedelta(days=1)
        return defaults

    force_unlock = fields.Boolean("Mở khóa thủ công", default=False, tracking=True)

    @api.depends('date', 'force_unlock')
    def _compute_status(self):
        for rec in self:
            today = fields.Date.context_today(rec)
            if rec.force_unlock:
                rec.status = 'open'
            else:
                rec.status = 'open' if today <= rec.date else 'lock'
                
    def action_force_unlock(self):
        for rec in self:
            rec.force_unlock = True

    def action_force_lock(self):
        for rec in self:
            rec.force_unlock = False
    
    @api.onchange('date')
    def _onchange_state(self):
        for rec in self:
            rec.name = _('Đăng ký xe ngày %s') % rec.date.strftime('%d/%m/%Y')

    def action_sale_vehicle_in_out_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Thêm xe'),
            'res_model': 'sale.vehicle.in.out.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_vehicle_in_out_id': self.id,
                'default_type': self.type,
            },
        }

    def action_send_to_conveyor(self):
        for line in self.line_ids.filtered(lambda l: not l.to_push and not l.is_next_day):
            line.send_to_conveyor()

    def _cron_send_to_conveyor(self, cur_date=None):
        if not cur_date:
            cur_date = datetime.date.today()
        model_ids = self.search([('date','=',cur_date),('status','!=','lock')])
        for line in model_ids.line_ids.filtered(lambda l: l.date_end):
            line.action_update_fields_to_picking()
        for line in model_ids.line_ids.filtered(lambda l: not l.to_push and not l.is_next_day):
            line.send_to_conveyor()
