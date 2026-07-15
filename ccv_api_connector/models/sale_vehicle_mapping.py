from odoo import models, fields, api

class SaleVehicleMapping(models.Model):
    _name = 'sale.vehicle.mapping'
    _description = 'Vehicle Mapping'

    name = fields.Char("Name")
    model = fields.Char("Model",required=True)
    key = fields.Char("Key",required=True)
    record_id = fields.Char("Record ID",required=True)

class SaleVehicleConveyorMapping(models.Model):
    _name = 'sale.vehicle.conveyor.mapping'
    _description = 'Conveyor Mapping'
    _rec_name = 'conveyor_gate'

    conveyor_gate = fields.Char("Conveyor Gate")
    conveyor_line_id = fields.Char("Conveyor Line ID")
