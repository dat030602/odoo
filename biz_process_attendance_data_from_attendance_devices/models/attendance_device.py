# -*- coding: utf-8 -*-


import logging
from odoo import models, fields


_logger = logging.getLogger(__name__)


class AttendanceDevice(models.Model):
    _inherit = "attendance.device"

    is_not_create_attendance_data_by_state = fields.Boolean(string="Is not create attendance data by state", default=False)

