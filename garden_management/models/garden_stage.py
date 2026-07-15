from odoo import fields, api, models


class GardenStage(models.Model):
    _name = "garden.stage"
    _order = "sequence"

    name = fields.Char(string="Tên")
    duration = fields.Integer(string="Thời gian")
    uom_id = fields.Many2one(
            'uom.uom', 
            string="Loại thời gian",
            domain=lambda self: '%s' % [('category_id', '=', int(self.env.ref('garden_management.garden_management_uom_category_id').sudo().value))]
        )
    note = fields.Text(string="Ghi chú")
    garden_care_ids = fields.Many2many('garden.care',string='Cách chăm sóc')
    sequence = fields.Integer(default=1)
