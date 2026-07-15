from odoo import api, fields, models, tools, _
from odoo.tools import image
from geopy.geocoders import Nominatim
from odoo.http import request

class SaleRouteReport(models.Model):
    _name = 'sale.route.report'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'sale.route.report'

    checkin_latitude =  fields.Float('Check-in Latitude', digits=(10,7))
    checkin_longitude = fields.Float('Check-in Longitude', digits=(10,7))
    tolerance = fields.Float(string="Tolerance")
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='cascade')
    sale_person_id = fields.Many2one(comodel_name='res.users', related='partner_id.user_id', store=True)
    user_id = fields.Many2one('res.users', string='Checked in by')
    checkin_image = fields.Binary("Check-in Image")
    checkin_date = fields.Datetime('Check-in Date')
    checkin_status = fields.Selection(
        string='Check-in Status',
        selection=[('successful', 'Successful'), ('failed', 'Unsuccessful')]
    )
    sale_route_group_id = fields.Many2one('sale.route.group','Sale route group', readonly=True)
    checkin_address = fields.Char('Check-in Address', compute="compute_address_checkin", store=True)
    checkout_latitude =  fields.Float('Check-out Latitude', digits=(10,7))
    checkout_longitude = fields.Float('Check-out Longitude', digits=(10,7))
    checkout_date = fields.Datetime('Check-out Date')
    checkout_status = fields.Selection(
        string='Check-out Status',
        selection=[('successful', 'Successful'), ('failed', 'Unsuccessful')]
    )
    checkout_image = fields.Binary("Check-out Image")
    checkout_address = fields.Char('Check-out Address', compute="compute_address_checkout", store=True)
    time = fields.Float('Time', compute="compute_time", store=True)
    sale_route_line_id = fields.Many2one('sale.route.line')
    sale_route_id = fields.Many2one('sale.route',related='sale_route_line_id.sale_route_id', store=True)
    sale_route_code = fields.Char('Sale route',  related='sale_route_id.code')
    # company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('checkin_date','checkout_date')
    def compute_time(self):
        for res in self:
            if res.checkin_date and res.checkout_date:
                duration = res.checkout_date - res.checkin_date
                date = duration.days
                hour = duration.seconds/3600
                res.time = duration.seconds/3600 + date * 24
            else:
                res.time = 0

    def down_load_checkin_image(self):
        return {
            'target': 'new',
            'type': 'ir.actions.act_url',
            'url': '/web/content/sale.route.report/%s/checkin_image?download=1' % self.id
        }
    def down_load_checkout_image(self):
        return {
            'target': 'new',
            'type': 'ir.actions.act_url',
            'url': '/web/content/sale.route.report/%s/checkout_image?download=1' % self.id
        }

    @api.depends('checkin_latitude','checkin_longitude','partner_id')
    def compute_address_checkin(self):
        for res in self:
            res.checkin_address = res.partner_id.street

    @api.depends('checkout_latitude','checkout_longitude','partner_id')
    def compute_address_checkout(self):
        for res in self:
            res.checkout_address = res.partner_id.street

