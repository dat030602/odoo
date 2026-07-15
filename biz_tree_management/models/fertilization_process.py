from odoo import api, fields, models, _
    
class FertilizationProcess(models.Model):
    _name = "tree.management.fertilization.process"
    _description = "Fertilization Process"
    
    name = fields.Char("Fertilization Process Name")
    dosage = fields.Float("Dosage")
    plant_type_id = fields.Many2one("tree.management.plant.type", "Plant Type")
    fertilization_time = fields.Datetime("Fertilization Time")
    description = fields.Text("Description")