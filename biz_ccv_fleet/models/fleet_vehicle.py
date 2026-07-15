from odoo import api, fields, models, tools, _

class FleetVehicleLogServices(models.Model):
	_inherit = 'fleet.vehicle.log.services'

	type_service = fields.Selection([
			('service', 'Services'),
			('registration', 'Registration'),
			('maintenance', 'Maintenance')
		], string="Type", default='service')

	fleet_service_id = fields.Many2one("fleet.vehicle.log.services", 'Service')
	name_service = fields.Char(string='Name', compute="_compute_name_service", copy=False, readonly=True)
	
	@api.depends('type_service')
	def _compute_name_service(self):
		for res in self:
			name_service = ''
			id = '' if isinstance(res.id, models.NewId) else str(res.id)
			if res.type_service == 'registration':
				name_service = 'DVDK' + id
			elif res.type_service == 'maintenance':
				name_service = 'DVBD' + id
			elif res.type_service == 'service':
				name_service = 'DV' + id
			res.name_service = name_service