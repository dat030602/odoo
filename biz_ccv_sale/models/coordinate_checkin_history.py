from odoo import api, fields, models, tools, _
from odoo.tools import image


class CoordinateCheckinHistory(models.Model):
    _name = 'coordinate.checkin.history'
    _description = 'Coordinate Checkin History'
    _order = 'checkin_date DESC'

    latitude = fields.Float('Latitude', digits=(10,7))
    Longitude = fields.Float('Longitude', digits=(10,7))
    tolerance = fields.Float(string="Tolerance")
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='cascade')
    sale_person_id = fields.Many2one(comodel_name='res.users', related='partner_id.user_id', store=True)
    user_id = fields.Many2one('res.users', string='Check-in Person')
    checkin_image = fields.Binary("Check-in Image")
    checkin_date = fields.Datetime('Check-in Date')
    status = fields.Selection(
        string='Status',
        selection=[('successful', 'Successful'), ('failed', 'Unsuccessful')]
    )
    sale_route_id = fields.Many2one("sale.route", 'Sale route')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)