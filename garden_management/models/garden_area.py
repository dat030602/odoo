from odoo import fields, api, models, _
from odoo.exceptions import ValidationError


class GardenArea(models.Model):
    _name = "garden.area"
    _description = "Thông tin khu vực trồng cây"
    _parent_store = True
    _parent_name = "parent_id"
    _rec_name = "complete_name"

    name = fields.Char(
        string="Tên khu vực", required=True, help="Tên của khu vực trồng cây"
    )
    complete_name = fields.Char(
        string="Tên đầy đủ",
        compute="_compute_complete_name",
        store=True,
        help="Tên đầy đủ của khu vực, bao gồm cả khu vực cha",
        recursive=True
    )
    parent_id = fields.Many2one(
        "garden.area",
        string="Khu vực cha",
        ondelete="restrict",
        help="Khu vực cha của khu vực hiện tại",
    )
    child_ids = fields.One2many(
        "garden.area",
        "parent_id",
        string="Khu vực con",
        help="Các khu vực con thuộc khu vực hiện tại",
    )
    area_type = fields.Selection(
        [("field", "Ruộng"), ("garden", "Vườn"), ("plot", "Lô")],
        string="Loại khu vực",
        help="Loại khu vực (ruộng, vườn, lô)",
    )
    description = fields.Text(string="Mô tả", help="Mô tả chi tiết về khu vực")
    image = fields.Binary(string="Hình ảnh", help="Hình ảnh minh họa cho khu vực")
    location = fields.Char(string="Vị trí", help="Vị trí địa lý của khu vực")
    total_area = fields.Float(
        string="Diện tích (m²)", help="Tổng diện tích của khu vực (mét vuông)"
    )
    note = fields.Text(string="Ghi chú", help="Các ghi chú khác về khu vực")
    parent_path = fields.Char(index=True)

    tree_count = fields.Integer(string="Số lượng cây", compute="_compute_tree_count")
    planted_tree_count = fields.Integer(string="Số cây đã trồng", compute="_compute_planted_tree_count")
    dead_tree_count = fields.Integer(string="Số cây đã chết", compute="_compute_dead_tree_count")
    last_planting_date = fields.Date(string="Lần cuối trồng cây", compute="_compute_last_planting")
    last_planting_tree = fields.Char(string="Cây trồng cuối", compute="_compute_last_planting")
    tree_count_by_type = fields.Integer(string="Số lượng cây theo loại", compute="_compute_tree_count_by_type")
    code = fields.Char(string="Mã khu vườn", required=True)
    sequence_id = fields.Many2one('ir.sequence')

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for record in self:
            if record.parent_id:
                record.complete_name = (
                    f"{record.parent_id.complete_name} / {record.name}"
                )
            else:
                record.complete_name = record.name

    @api.constrains("parent_id")
    def _check_hierarchy(self):
        if not self._check_recursion():
            raise ValidationError(_("Lỗi! Bạn không thể tạo khu vực cha là con của nó."))

    @api.depends("child_ids")
    def _compute_tree_count(self):
        for record in self:
            total_count = 0
            area_ids = record.child_ids.ids + record.ids
            total_count = self.env["garden.plan.tree"].search_count([("area_id", "in", area_ids)])
            record.tree_count = total_count

    @api.depends("child_ids")
    def _compute_planted_tree_count(self):
        for record in self:
            total_count = 0
            area_ids = record.child_ids.ids + record.ids
            total_count = self.env["garden.plan.tree"].search_count([("area_id", "in", area_ids), ("state", "in", ["new", "developing"])])
            record.planted_tree_count = total_count

    @api.depends("child_ids")
    def _compute_dead_tree_count(self):
        for record in self:
            total_count = 0
            area_ids = record.child_ids.ids + record.ids
            total_count = self.env["garden.plan.tree"].search_count([("area_id", "in", area_ids), ("state", "=", "dead")])
            record.dead_tree_count = total_count

    @api.depends("child_ids")
    def _compute_last_planting(self):
        for record in self:
            area_ids = record.child_ids.ids + record.ids
            last_plan = self.env["garden.plan.tree"].search([("area_id", "in", area_ids)], order="date_start desc", limit=1)
            if last_plan:
                record.last_planting_date = last_plan.date_start
                record.last_planting_tree = last_plan.tree_id.name
            else:
                record.last_planting_date = False
                record.last_planting_tree = False

    @api.depends("child_ids")
    def _compute_tree_count_by_type(self):
        for record in self:
            area_ids = record.child_ids.ids + record.ids
            total_count = self.env["garden.plan.tree"].search_count([("area_id", "in", area_ids)])
            record.tree_count_by_type = total_count

    def get_planted_tree_all(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Trồng cây",
            "context": "{'search_default_area_id': active_id}",
            'res_model': 'garden.plan.tree',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    
    def get_planted_tree_call(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Trồng cây",
            "context": "{'search_default_area_id': active_id, 'search_default_state': ['new', 'developing']}",
            'res_model': 'garden.plan.tree',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def get_dead_tree_call(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Trồng cây",
            "context": "{'search_default_area_id': active_id, 'search_default_state': ['dead']}",
            'res_model': 'garden.plan.tree',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def get_tree_by_type_call(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Trồng cây",
            "context": "{'search_default_area_id': active_id, 'group_by': 'tree_id'}",
            'res_model': 'garden.plan.tree',
            'view_mode': 'tree,form',
            'target': 'current',
        }
    @api.model_create_multi
    def create(self, vals_list):
        res = super(GardenArea, self).create(vals_list)
        sequence_env = self.env['ir.sequence'].sudo()
        sequence_id = sequence_env.create({
            'name':'garden.area %s' % res.name,
            'code':'garden.area',
            'prefix': res.code,
            'padding':3,
            'number_increment': 1,
            'number_next': 1,
            'implementation':'standard'
        })
        res.sequence_id = sequence_id
        return res
