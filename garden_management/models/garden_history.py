from odoo import fields, api, models

from datetime import datetime

class GardenStage(models.Model):
    _name = "garden.history"
    _order = "date"

    name = fields.Char(string="Tên")
    type = fields.Selection(string='Loại', selection=[
        ('plan','Trồng cây'),
        ('note','Ghi nhận hàng ngày'),
        ('disease','Bệnh'),
    ])
    date = fields.Date(string="Thời gian", default=fields.Datetime.today().date())
    note = fields.Text(string="Nội dung")
    plan_id = fields.Many2one('garden.plan.tree', 'Mã trồng')
    tree_id = fields.Many2one('garden.tree', 'Cây')
    area_id = fields.Many2one('garden.area', 'Khu vực')
    current_stage_id = fields.Many2one('garden.area',string='Giai đoạn hiện tại')
    state = fields.Selection(string="Trạng thái", selection=[
        ('new', 'Mới'),
        ('posted', 'Đã đăng')
    ], default='new')

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        for rec in self:
            if rec.plan_id:
                rec.tree_id = rec.plan_id.tree_id
                rec.area_id = rec.plan_id.area_id
                rec.current_stage_id = rec.plan_id.current_stage_id.id
            else:
                rec.tree_id = False
                rec.area_id = False
                rec.current_stage_id = False

    def action_post(self):
        self.state = 'posted'
        
    def action_unpost(self):
        self.state = 'new'