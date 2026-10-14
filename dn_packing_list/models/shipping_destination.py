# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ShippingDestination(models.Model):
    _name = 'shipping.destination'
    _description = 'shipping.destination'

    name = fields.Char(string="Stage Name", required=True)
    active = fields.Boolean(string="Active",default=True)
    code = fields.Char(string="Code")
    description = fields.Text(string="Description")
    notes = fields.Text(string="Notes")
    sequence = fields.Integer(string="Sequence", default=lambda self: self.env['ir.sequence'].next_by_code('sequence_shipping_destination'))