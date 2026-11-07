# -*- coding: utf-8 -*-
"""Configurable Python modules exposed to template scripts."""

import importlib

from odoo import _, api, fields, models
from odoo.exceptions import UserError


DEFAULT_ALLOWED_MODULES = (
    'ast',
    'base64',
    'datetime',
    'decimal',
    'hashlib',
    'hmac',
    'json',
    'math',
    'random',
    're',
)


class ExcelReportPythonModule(models.Model):
    _name = 'excel.report.python.module'
    _description = 'Excel Report Python Module'
    _order = 'name, id'

    name = fields.Char(
        string='Module Name',
        required=True,
        index=True,
        help='Exact Python import name exposed to Python Code templates.',
    )
    active = fields.Boolean(
        string='Enabled',
        default=False,
        readonly=True,
        help='Only enabled modules are exposed to Python Code templates.',
    )

    _module_name_unique = models.Constraint(
        'UNIQUE(name)',
        'A Python module with this name already exists.',
    )

    def action_test_module(self):
        """Verify that the exact module name is installed, then enable it."""
        self.ensure_one()
        module_name = (self.name or '').strip()
        if not module_name:
            raise UserError(_('Please enter a Python module name first.'))
        try:
            importlib.import_module(module_name)
        except (ImportError, ModuleNotFoundError) as error:
            raise UserError(
                _("Python module '%s' is not available in this Odoo environment: %s")
                % (module_name, error)
            ) from error
        self.write({'name': module_name, 'active': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Module Test Passed'),
                'message': _("Python module '%s' is now enabled for Python Code templates.") % module_name,
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def _get_allowed_modules(self):
        """Return only explicitly safe defaults and tested active modules."""
        modules = {}
        for module_name in DEFAULT_ALLOWED_MODULES:
            modules[module_name] = importlib.import_module(module_name)
        for module in self.search([('active', '=', True)]):
            try:
                modules[module.name] = importlib.import_module(module.name)
            except (ImportError, ModuleNotFoundError) as error:
                raise UserError(
                    _("Enabled Python module '%s' is no longer available: %s")
                    % (module.name, error)
                ) from error
        return modules
