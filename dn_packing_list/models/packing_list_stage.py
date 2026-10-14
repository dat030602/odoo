# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class PackingListStage(models.Model):
    _name = 'packing.list.stage'
    _description = 'Packing List Stages'
    _order = 'sequence'

    sequence = fields.Integer(string="Sequence", default=10)
    name = fields.Char(string="Stage Name", required=True)
    is_new = fields.Boolean(string="New")
    is_packing = fields.Boolean(string="Packing")
    is_loading = fields.Boolean(string="Loading")
    is_review = fields.Boolean(string="Review")
    is_delivery = fields.Boolean(string="Need Delivery")
    is_invoice = fields.Boolean(string="Need Invoice")
    is_closed = fields.Boolean(string="Closed")
    active = fields.Boolean(string="Active", default=True)

