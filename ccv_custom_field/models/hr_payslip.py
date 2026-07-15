from odoo import models, fields, api
import logging
from datetime import datetime
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    advance_salary_day = fields.Integer(string='Ngày tạm ứng',related="payslip_run_id.advance_salary_day")
