# -*- coding: utf-8 -*-
"""Table loop datasources and columns for Excel Report Templates."""

import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

NAME_REGEX = re.compile(r'^[a-z_][a-z0-9_]*$')


class ExcelReportDatasource(models.Model):
    _name = 'excel.report.datasource'
    _description = 'Excel Report Datasource'
    _order = 'name, id'

    template_id = fields.Many2one(
        'excel.report.template',
        string='Template',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(
        string='Datasource Name',
        required=True,
        help="Identifier used in placeholders (e.g. 'summary' for ${table:summary.product})",
    )
    rows_expr = fields.Char(
        string='Rows Expression',
        required=True,
        help="Python expression returning an iterable of record lines (e.g. 'record.order_line')",
    )
    column_ids = fields.One2many(
        'excel.report.datasource.column',
        'datasource_id',
        string='Columns',
        copy=True,
    )

    _uniq_template_ds_name = models.Constraint(
        'UNIQUE(template_id, name)',
        'Datasource name must be unique per template!',
    )

    @api.constrains('name')
    def _check_name_format(self):
        for rec in self:
            if not rec.name or not NAME_REGEX.match(rec.name):
                raise ValidationError(
                    _("Datasource name '%s' is invalid. It must start with a lowercase letter or underscore, and contain only lowercase letters, digits, and underscores (e.g. 'order_lines').")
                    % rec.name
                )

    @api.constrains('rows_expr')
    def _check_rows_expr(self):
        for rec in self:
            if not rec.rows_expr:
                continue
            try:
                compile(rec.rows_expr.strip(), f'<datasource:{rec.name}:rows>', 'eval')
            except Exception as e:
                raise ValidationError(
                    _("Syntax error in rows expression for datasource '%s': %s")
                    % (rec.name, str(e))
                )


class ExcelReportDatasourceColumn(models.Model):
    _name = 'excel.report.datasource.column'
    _description = 'Excel Report Datasource Column'
    _order = 'sequence, key, id'

    datasource_id = fields.Many2one(
        'excel.report.datasource',
        string='Datasource',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    key = fields.Char(
        string='Column Key',
        required=True,
        help="Column identifier matching template placeholder (e.g. 'product' for ${table:summary.product})",
    )
    expr = fields.Char(
        string='Cell Expression',
        required=True,
        help="Expression evaluated for each line (available variables: 'line', 'idx', 'record', 'company', etc.)",
    )

    _uniq_ds_col_key = models.Constraint(
        'UNIQUE(datasource_id, key)',
        'Column key must be unique per datasource!',
    )

    @api.constrains('key')
    def _check_key_format(self):
        for rec in self:
            if not rec.key or not NAME_REGEX.match(rec.key):
                raise ValidationError(
                    _("Column key '%s' is invalid. It must contain only lowercase letters, digits, and underscores.")
                    % rec.key
                )

    @api.constrains('expr')
    def _check_expr_syntax(self):
        for rec in self:
            if not rec.expr:
                continue
            try:
                compile(rec.expr.strip(), f'<column:{rec.key}>', 'eval')
            except Exception as e:
                raise ValidationError(
                    _("Syntax error in cell expression for column '%s': %s")
                    % (rec.key, str(e))
                )
