from odoo import fields, api, models


class GardenCare(models.Model):
    _name = "garden.care"
    _description = "Garden Care Activities"

    name = fields.Char(string="Tên hoạt động", required=True)
    care_type = fields.Selection([
        ('watering', 'Tưới nước'),
        ('fertilizing', 'Bón phân'),
        ('pruning', 'Tỉa cành'),
        ('pest_control', 'Kiểm soát sâu bệnh'),
        ('other', 'Khác')
    ], string="Loại hoạt động chăm sóc", required=True)
    note = fields.Text(string="Ghi chú")
    garden_fertilizer_usage_ids = fields.Many2many('garden.fertilizer.usage', string='Cách chăm sóc')
    garden_proportion_ids = fields.Many2many('garden.proportion', string='Tỷ lệ')


