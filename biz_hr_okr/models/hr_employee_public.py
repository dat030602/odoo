from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    parent_ids = fields.One2many('hr.employee.public', string='Superiors', compute='_compute_managers', search='_search_parent_ids',
                                  help="Direct and indirect managers", compute_sudo=True)
