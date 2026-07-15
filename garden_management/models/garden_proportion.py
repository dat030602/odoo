from odoo import fields, api, models


class GardenProportion(models.Model):
    _name = "garden.proportion"

    name = fields.Char(string="Tỷ lệ")
    fertilizer_ids = fields.Many2many('garden.fertilizer', string="Phân bón", required=True)
