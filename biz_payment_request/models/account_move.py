# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):

	_inherit = "account.move"
	
	payment_request_id = fields.Many2one('payment.request', string="Đề nghị thanh toán")