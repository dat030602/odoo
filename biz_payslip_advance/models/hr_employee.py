# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class Employee(models.Model):
    _inherit = "hr.employee"

    code = fields.Char('Code')

class Employee(models.Model):
    _inherit = "hr.employee.public"

    code = fields.Char('Code')
    