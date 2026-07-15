from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """
        Dirty hack to allow HR officer to update employee's private address without res.users access rights error
        """
        if self._name == 'res.users' and self.env.user.has_group('hr.group_hr_user') and operation == 'write' and self._context.get('group_hr_user_update_private_address', False):
            return True
        return super(ResUsers, self).check_access_rights(operation, raise_exception)
