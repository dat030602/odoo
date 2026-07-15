from odoo import models, fields, _
import logging
from datetime import datetime
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class HrLeave(models.Model):
    _inherit = "hr.leave"

    def _get_responsible_for_approval(self):
        self.ensure_one()

        responsible = self.env.user

        if self.holiday_type != 'employee':
            return responsible
        
        env_params = self.env['ir.config_parameter'].sudo()
        hr_director_id = env_params.get_param('ccv_bao_cao.director_id', default=False)
        hr_director_id = self.env['res.users'].browse(int(hr_director_id)) if hr_director_id else False

        if self.employee_id.leave_manager_id:
            leave_manager_id = self.employee_id.leave_manager_id
        elif self.employee_id.parent_id.user_id:
            leave_manager_id = self.employee_id.parent_id.user_id
        else:
            leave_manager_id = self.env.user

        if self.holiday_status_id.responsible_id:
            responsible_id = self.holiday_status_id.responsible_id
        else:
            responsible_id = self.env.user

        if hr_director_id and leave_manager_id == hr_director_id:
            leave_manager_id = responsible_id
            responsible_id = hr_director_id

        if self.validation_type == 'manager' or (self.validation_type == 'both' and self.state == 'confirm'):
            responsible = leave_manager_id
        elif self.validation_type == 'hr' or (self.validation_type == 'both' and self.state == 'validate1'):
            responsible = responsible_id

        return responsible
    