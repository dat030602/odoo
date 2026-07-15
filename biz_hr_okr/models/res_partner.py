from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # 'employee' is a field of 'base' module but does not display on any view or use in anywhere,
    # so I make use for it here
    employee = fields.Boolean(compute='_compute_is_employee', store=True, groups='hr.group_hr_user')

    @api.depends('employee_ids')
    def _compute_is_employee(self):
        for r in self:
            r.employee = bool(r.employee_ids)

    def _get_hr_allowed_fields(self):
        return self._address_fields() + ['phone', 'mobile', 'email', 'dob', 'bank_ids', 'name', 'company_id', 'type']

    def write(self, vals):
        """
        Dirty hack to allow HR officer to update employee's private address without res.users access rights error
        """
        if self.env.user.has_group('hr.group_hr_user') and all(f in self._get_hr_allowed_fields() for f in vals.keys()):
            return super(ResPartner, self.with_context(group_hr_user_update_private_address=True)).write(vals)
        return super(ResPartner, self).write(vals)
