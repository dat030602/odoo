import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    vn_id_type = fields.Selection(
        selection=[
            ('cccd', 'Citizen Identity Card (CCCD/12 digits)'),
            ('cmnd', 'Identity Card (CMND/9 digits)'),
            ('other', 'Other Identification'),
        ],
        string="ID Card Type",
        default='cccd',
        tracking=True,
        groups="hr.group_hr_user",
    )
    vn_id_number = fields.Char(
        string="ID Card Number",
        copy=False,
        tracking=True,
        index=True,
        groups="hr.group_hr_user",
    )
    vn_id_issue_date = fields.Date(
        string="Issue Date",
        tracking=True,
        groups="hr.group_hr_user",
    )
    vn_id_issue_place = fields.Char(
        string="Place of Issue",
        tracking=True,
        groups="hr.group_hr_user",
    )
    vn_id_expiry_date = fields.Date(
        string="Expiry Date",
        tracking=True,
        groups="hr.group_hr_user",
    )
    vn_id_image_front = fields.Binary(
        string="Front Image",
        attachment=True,
        groups="hr.group_hr_user",
    )
    vn_id_image_back = fields.Binary(
        string="Back Image",
        attachment=True,
        groups="hr.group_hr_user",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if isinstance(vals.get('vn_id_number'), str):
                vals['vn_id_number'] = vals['vn_id_number'].strip()
            if vals.get('vn_id_number') and not vals.get('identification_id'):
                vals['identification_id'] = vals['vn_id_number']
        return super().create(vals_list)

    def write(self, vals):
        if isinstance(vals.get('vn_id_number'), str):
            vals['vn_id_number'] = vals['vn_id_number'].strip()

        # If vn_id_number is being updated and identification_id is not explicitly passed:
        if vals.get('vn_id_number') and 'identification_id' not in vals:
            # If all records lack identification_id, optimize by setting in vals directly
            if not any(self.mapped('identification_id')):
                vals['identification_id'] = vals['vn_id_number']

        res = super().write(vals)

        # In case the recordset was mixed (some had identification_id, some didn't):
        if vals.get('vn_id_number') and 'identification_id' not in vals:
            records_to_sync = self.filtered(lambda emp: not emp.identification_id)
            if records_to_sync:
                records_to_sync.write({'identification_id': vals['vn_id_number']})

        return res

    @api.constrains('vn_id_number', 'vn_id_type')
    def _check_vn_id_number_format(self):
        for employee in self:
            if not employee.vn_id_number:
                continue
            number = employee.vn_id_number.strip()
            if employee.vn_id_type == 'cccd':
                if not re.fullmatch(r'\d{12}', number):
                    raise ValidationError(
                        _("Citizen Identity Card (CCCD) number must contain exactly 12 digits. Provided: %(number)s",
                          number=number)
                    )
            elif employee.vn_id_type == 'cmnd':
                if not re.fullmatch(r'\d{9}', number):
                    raise ValidationError(
                        _("Identity Card (CMND) number must contain exactly 9 digits. Provided: %(number)s",
                          number=number)
                    )

    @api.constrains('vn_id_number', 'active')
    def _check_vn_id_number_unique(self):
        active_records = self.filtered(lambda emp: emp.active and emp.vn_id_number)
        if not active_records:
            return

        # 1. Check uniqueness within the current batch
        seen_numbers = {}
        for emp in active_records:
            number = emp.vn_id_number.strip()
            if number in seen_numbers:
                raise ValidationError(
                    _("The ID Card Number '%(number)s' is duplicated within the submitted records (employees '%(name1)s' and '%(name2)s').",
                      number=number, name1=seen_numbers[number].name, name2=emp.name)
                )
            seen_numbers[number] = emp

        # 2. Check uniqueness against existing active records in database (single query)
        duplicates = self.sudo().search([
            ('id', 'not in', active_records.ids),
            ('active', '=', True),
            ('vn_id_number', 'in', list(seen_numbers.keys())),
        ])
        if duplicates:
            duplicate = duplicates[0]
            raise ValidationError(
                _("The ID Card Number '%(number)s' is already registered for active employee '%(name)s'.",
                  number=duplicate.vn_id_number, name=duplicate.name)
            )

    @api.constrains('vn_id_issue_date', 'vn_id_expiry_date', 'birthday')
    def _check_vn_id_dates(self):
        today = fields.Date.today()
        for employee in self:
            if employee.vn_id_issue_date and employee.vn_id_issue_date > today:
                raise ValidationError(
                    _("The ID card issue date cannot be in the future.")
                )
            if employee.vn_id_issue_date and employee.vn_id_expiry_date:
                if employee.vn_id_expiry_date <= employee.vn_id_issue_date:
                    raise ValidationError(
                        _("The ID card expiry date must be strictly after the issue date.")
                    )
            if employee.birthday and employee.vn_id_issue_date:
                if employee.vn_id_issue_date < employee.birthday:
                    raise ValidationError(
                        _("The ID card issue date cannot be earlier than the date of birth.")
                    )

    @api.onchange('vn_id_number')
    def _onchange_vn_id_number(self):
        if self.vn_id_number and not self.identification_id:
            self.identification_id = self.vn_id_number.strip()
