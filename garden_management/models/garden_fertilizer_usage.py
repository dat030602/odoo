from odoo import fields, api, models


class GardenFertilizerUsage(models.Model):
    _name = "garden.fertilizer.usage"
    _description = "Garden Fertilizer Usage"

    name = fields.Char(string="Tên", required=True)
    fertilizer_id = fields.Many2one('garden.fertilizer', string="Phân bón", required=True)
    quantity = fields.Float(string="Số lượng sử dụng", required=True)
    uom_id = fields.Many2one('uom.uom', string="Đơn vị tính", related="fertilizer_id.uom_id", readonly=True)
    date_used = fields.Integer(string="Ngày sử dụng")
    note = fields.Text(string="Ghi chú")
    
    @api.onchange('fertilizer_id')
    def _onchange_fertilizer(self):
        if self.fertilizer_id:
            self.uom_id = self.fertilizer_id.uom_id
