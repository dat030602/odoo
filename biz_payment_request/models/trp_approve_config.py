# -*- coding: utf-8 -*-

from odoo import models, fields, api

class TrpApproveHistory(models.Model):
	_inherit = 'trp.approve.config'
 
	response_cash_id = fields.Many2one('res.users', string="Người thanh toán tiền mặt")
	response_bank_id = fields.Many2one('res.users', string="Người thanh toán qua ngân hàng")
