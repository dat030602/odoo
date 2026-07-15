# -*- coding: utf-8 -*-

from odoo import fields, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    is_write_by_cron = fields.Boolean(string="Is write by cron", default=False)
    is_create_by_cron = fields.Boolean(string="Is create by cron", default=False)
