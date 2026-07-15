from odoo import fields, api, models
from odoo.tools import pytz
from datetime import datetime, timedelta
from odoo import exceptions, _

class GardenPlanTree(models.Model):
    _name = "garden.plan.tree"
    _description = "Kế hoạch trồng cây"

    code = fields.Char(string="Mã cây", help="Mã định danh cho cây trồng", readonly=True)
    name = fields.Char(string="Tên", required=True, help="Tên cây trồng", compute="_compute_name")
    date_start = fields.Date(string="Ngày trồng", required=True, help="Ngày bắt đầu trồng cây")
    tree_id = fields.Many2one('garden.tree', string='Cây', required=True, help="Loại cây được trồng")
    area_id = fields.Many2one('garden.area', string='Khu vực', required=True, help="Khu vực trồng cây")
    stage_apply_ids = fields.Many2many('garden.stage', string='Giai đoạn cây trồng', related='tree_id.stage_ids', help="Các giai đoạn phát triển của cây")
    current_stage_id = fields.Many2one('garden.stage', string='Giai đoạn hiện tại', compute="_compute_stage", store=True, help="Giai đoạn hiện tại của cây")
    state = fields.Selection(string='Trạng thái', selection=[
        ('draft','Nháp'),
        ('new','Mới trồng'),
        ('developing','Đang phát triển'),
        ('dead', 'Đã chết'),
    ],default='draft', help="Trạng thái hiện tại của cây")
    note = fields.Text(string="Ghi chú", help="Các ghi chú khác về kế hoạch trồng cây")

    @api.depends('code','tree_id')
    def _compute_name(self):
        for rec in self:
            if rec.tree_id:
                rec.name = '%s%s' % (('[%s] ' % rec.code) if rec.code else '', rec.tree_id.name)
            else:
                rec.name = '/'

    @api.depends('date_start', 'stage_apply_ids')
    def _compute_stage(self):
        for record in self:
            current_stage_id = self.env['garden.stage']
            if record.stage_apply_ids and record.date_start:
                now_time = datetime.now()
                user = self.env.user
                tz = pytz.timezone(user.tz) if user.tz else pytz.utc
                user_tz_date = pytz.utc.localize(now_time).astimezone(tz).date()
                
                planting_date = record.date_start
                time_diff = (user_tz_date - planting_date).days

                total_duration = 0
                for stage in record.stage_apply_ids:
                  
                    total_duration += stage.duration
                    if time_diff <= total_duration :
                        current_stage_id = stage
                        break
                record.current_stage_id = current_stage_id

    @api.onchange('date_start', 'stage_apply_ids', 'current_stage_id', 'tree_id')
    def _onchange_current_stage_id(self):
        for record in self:
            if record.current_stage_id:
               if record.current_stage_id == record.stage_apply_ids[0]:
                   record.state = 'new'
               else:
                    record.state = 'developing'
            else:
                if record.state != 'dead':
                    record.state = 'draft'

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, '%s - %s' % (rec.code, rec.name)))
        return result

    def action_mark_dead(self):
        for record in self:
             record.state = 'dead'
    
    def action_mark_new(self):
        for record in self:
             record.state = 'new'

    @api.model
    def create(self, vals_list):
        if 'area_id' in vals_list:
            area = self.env['garden.area'].browse(vals_list['area_id'])
            if area.sequence_id:
                sequence = area.sequence_id
                vals_list['code'] = sequence.next_by_id()
        res = super(GardenPlanTree, self).create(vals_list)
        history_env = self.env['garden.history']
        history_env.create({
            'name':'Trồng cây %s ở %s' % (res.name, res.area_id.complete_name),
            'type':'plan',
            'date': res.date_start,
            'plan_id':res.id,
        })
        return res
