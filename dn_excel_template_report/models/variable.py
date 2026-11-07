# -*- coding: utf-8 -*-
"""Custom runtime variables for Excel Report Templates."""

import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

NAME_REGEX = re.compile(r'^[a-z_][a-z0-9_]*$')


class ExcelReportVariable(models.Model):
    _name = 'excel.report.variable'
    _description = 'Excel Report Variable'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'excel.report.template',
        string='Template',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(
        string='Variable Name',
        required=True,
        help="Identifier used in placeholders (e.g. 'tax_included' for ${tax_included})",
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Variables with lower sequence numbers are evaluated first and accessible to later ones.',
    )
    code = fields.Char(
        string='Python Expression',
        required=True,
        help='Expression evaluated in the reporting context (e.g. record.amount_total * 0.1)',
    )
    value_type = fields.Selection(
        [
            ('auto', 'Auto'),
            ('text', 'Text'),
            ('number', 'Number'),
            ('date', 'Date'),
            ('image', 'Image'),
        ],
        string='Value Type',
        default='auto',
        required=True,
    )

    _uniq_template_var_name = models.Constraint(
        'UNIQUE(template_id, name)',
        'Variable name must be unique per template!',
    )

    @api.constrains('name')
    def _check_name_format(self):
        for rec in self:
            if not rec.name or not NAME_REGEX.match(rec.name):
                raise ValidationError(
                    _("Variable name '%s' is invalid. It must start with a lowercase letter or underscore, and contain only lowercase letters, digits, and underscores (e.g. 'my_variable').")
                    % rec.name
                )

    @api.constrains('code')
    def _check_code_syntax(self):
        for rec in self:
            if not rec.code:
                continue
            try:
                compile(rec.code.strip(), f'<variable:{rec.name}>', 'eval')
            except Exception as e:
                raise ValidationError(
                    _("Syntax error in variable expression for '%s': %s")
                    % (rec.name, str(e))
                )
