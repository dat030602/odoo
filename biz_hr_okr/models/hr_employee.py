from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    vat = fields.Char(string='Personal Tax Code', related='address_home_id.vat', store=True, readonly=False, groups="hr.group_hr_user",
                      help="The tax identification number that is related to the corresponding partner record specified in the field Private Address")
    parent_ids = fields.One2many('hr.employee', string='Superiors', compute='_compute_managers', search='_search_parent_ids',
                                  help="Direct and indirect managers", compute_sudo=True)

    @api.model_create_multi
    @api.returns('self', lambda value:value.id)
    def create(self, vals_list):
        records = super(HrEmployee, self).create(vals_list)
        # as Odoo caches ir.rules's result for performance, clearing cache
        # is required when creating new employees that may modify current
        # employee hierarchy
        self.env['ir.rule'].clear_caches()
        return records

    def write(self, vals):
        res = super(HrEmployee, self).write(vals)
        # as Odoo caches ir.rules's result for performance,
        # clearing cache is required when modifying employees' department and/or
        # direct manager that may modify current employee hierarchy is required
        if 'department_id' in vals or 'parent_id' in vals:
            self.env['ir.rule'].clear_caches()
        return res

    def unlink(self):
        res = super(HrEmployee, self).unlink()
        # as Odoo caches ir.rules's result for performance,
        # clearing cache when unlink employees that may modify
        # current employee hierarchy is required
        self.env['ir.rule'].clear_caches()
        return res
