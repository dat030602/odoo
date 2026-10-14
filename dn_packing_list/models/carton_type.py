# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class CartonType(models.Model):
    _name = 'carton.type'
    _description = 'Carton Type'

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(string="Active", default=True)
    cbm = fields.Float(string="Qty Per Ctn")
    qty_per_carton = fields.Float(
        string="Qty Per Carton",
        compute="_compute_qty_per_carton",
        inverse="_inverse_qty_per_carton",
        store=True,
    )

    @api.depends('cbm')
    def _compute_qty_per_carton(self):
        for rec in self:
            rec.qty_per_carton = rec.cbm

    def _inverse_qty_per_carton(self):
        for rec in self:
            rec.cbm = rec.qty_per_carton
    height = fields.Float(string="Height")
    length = fields.Float(string="Length")
    sequence = fields.Integer(string="Sequence")
    uom_id = fields.Many2one('uom.uom', string="UoM")
    weight = fields.Float(string="Weight")
    weight_uom = fields.Many2one('uom.uom', string="Weight UoM")
    width = fields.Float(string="Width")
    notes = fields.Text(string="Notes")
    partner_id = fields.Many2one('res.partner',string="Partner")
    product_id = fields.Many2one('product.template',string="Product")
    type = fields.Selection([
        ('carton', 'Carton'),
        ('pallet', 'Pallet'),
    ], string="Type")