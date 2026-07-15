from odoo import api, fields, models, _

class ManagementPlant(models.Model):
    _name = "tree.management.plant"
    _description = "Tree Management Plant"
    
    name = fields.Char("Plant Name")
    plant_type_id = fields.Many2one("tree.management.plant.type", "Plant Type")
    quantity = fields.Integer("Quantity", default=1)
    area_id = fields.Many2one("tree.management.area", "Areas")
    date = fields.Date("Date", default=fields.Date.today)
    

class ManagementPlantType (models.Model):
    _name = "tree.management.plant.type"
    _description = "Tree Management Plant Type"
    
    name = fields.Char("Plant Type Name")
    note = fields.Text("Note")
    
    
class ManagementArea(models.Model):
    _name = "tree.management.area"
    _description = "Tree Management Area"
    
    name = fields.Char("Area Name")
    area = fields.Float("Area")
    address = fields.Text("Address")
    