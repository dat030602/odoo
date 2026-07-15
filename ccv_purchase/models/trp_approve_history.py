# -*- coding: utf-8 -*-

from odoo import models, fields, api

class TrpApproveHistory(models.Model):
	_inherit = 'trp.approve.history'

	purchase_sign_requests_id = fields.Many2one('purchase.sign.requests', string="Purchase Sign Requests", ondelete='cascade')
