from odoo import models, fields, api


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    manager_ids = fields.One2many('hr.employee', string='Superiors', compute='_compute_managers',
                                  help="Direct and indirect managers", compute_sudo=True)
    recursive_child_ids = fields.Many2many('hr.department', 'parent_id', 'child_id', compute='_compute_recursive_child_ids',
                                           compute_sudo=True, string='Recursive Child Departments',
                                           help="Direct and Indirect Child Departments")
    name = fields.Char(translate=True)
    
    @api.depends('parent_id', 'manager_id', 'parent_id.manager_id')
    def _compute_managers(self):
        for r in self:
            r.manager_ids = r._get_recursive_managers()

    @api.depends('child_ids', 'child_ids.child_ids')
    def _compute_recursive_child_ids(self):
        for r in self:
            r.recursive_child_ids = r._get_recursive_children()

    @api.model_create_multi
    @api.returns('self', lambda value:value.id)
    def create(self, vals_list):
        records = super(HrDepartment, self).create(vals_list)
        # as Odoo caches ir.rules's result for performance,
        # clearing cache when creating new department that may modify
        # current employee hierarchy is required
        self.env['ir.rule'].clear_caches()
        return records

    def write(self, vals):
        res = super(HrDepartment, self).write(vals)
        # as Odoo caches ir.rules's result for performance,
        # clearing cache when modifying department that may modify
        # current employee hierarchy is required
        if 'manager_id' in vals or 'parent_id' in vals:
            self.env['ir.rule'].clear_caches()
        return res

    def unlink(self):
        res = super(HrDepartment, self).unlink()
        # as Odoo caches ir.rules's result for performance,
        # clearing cache when unlink department that may modify
        # current employee hierarchy is required
        self.env['ir.rule'].clear_caches()
        return res

    def _get_recursive_managers(self):
        managers = self.manager_id
        for parent in self.parent_id:
            managers |= parent._get_recursive_managers()
        return managers

    def _get_recursive_children(self):
        self.ensure_one()
        return self.search([('id', 'child_of', self.ids),('id','!=',self.id)])
