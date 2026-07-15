# -*- coding: utf-8 -*-

from odoo import models, fields, api

class TrpApproveHistory(models.Model):
	_inherit = 'trp.approve.history'
 
	payment_request_id = fields.Many2one('payment.request', string="Payment Request")