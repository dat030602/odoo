from odoo import api, fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    parent_all_count = fields.Integer(
        'Direct & Indirect Managers Count', recursive=True,
        compute='_compute_managers', store=False,
        compute_sudo=True)

    def _get_recursive_parents(self, children=None, department_manager=True):
        """
        This get all direct and indirect managers of the employee (excluding himself)
        To take the direct manager, just get the very first record of the returned result
        :param children: None or employee records to exclude himself from managers list
        :param department_manager: if False is given, managers of departments will not be taken into account
        """
        if not children:
            children = self.env[self._name]
        
        # find department managers (not include himself if he is the manager of the current department)
        if not department_manager:
            department_managers = self.env[self._name]
        else:
            department = self.department_id or self.env['hr.department'].search([('manager_id', 'in', self.ids)])
            department_managers = department._get_recursive_managers()

        parents = direct_parents = self.env[self._name]
        children |= self
        direct_parents |= self.parent_id + department_managers - children
        if direct_parents:
            parents |= direct_parents | direct_parents._get_recursive_parents(children, department_manager)
        return parents

    def _compute_parent_id(self):
        """
        Override to ensure employee itself will not be applied as its manager
        If it is the manager a department, its superior deparment's manager will become its manager
        """
        super(HrEmployeeBase, self)._compute_parent_id()
        for r in self.filtered(lambda emp: not emp.parent_id or emp.parent_id == emp.department_id.manager_id):
            r.parent_id = r._get_recursive_parents(department_manager=True)[:1]

    @api.depends_context('include_department_manager')
    @api.depends('parent_id', 'parent_id.parent_all_count', 'department_id', 'department_id.manager_id')
    def _compute_managers(self):
        for r in self:
            # sometimes we don't want department's managers
            department_manager = r._context.get('include_department_manager', True)
            r.parent_ids = r._get_recursive_parents(department_manager=department_manager)
            r.parent_all_count = len(r.parent_ids)

    def _search_parent_ids(self, operator, operand):
        all_employees = self.env[self._name].search([])
        if operator in ('ilike', 'not ilike', 'in', 'not in'):
            if operator in ('in', 'not in') and isinstance(operand, list):
                domain = [('id', operator, operand)]
            else:
                domain = [('name', operator, operand)]
            list_ids = [emp.id for emp in all_employees if emp.parent_ids.filtered_domain(domain)]
        elif operator == '=':
            if operand:  # equal
                list_ids = [emp.id for emp in all_employees if emp.parent_ids == operand]
            else:  # is not set, equal = ""
                list_ids = [emp.id for emp in all_employees if not emp.parent_ids]
        elif operator == '!=':
            if operand:
                list_ids = [emp.id for emp in all_employees if emp.parent_ids != operand]
            else:  # is set
                list_ids = [emp.id for emp in all_employees if emp.parent_ids]
        else:
            raise []
        return [('id', 'in', list_ids)]
