# -*- coding: utf-8 -*-
import json
import ast
import logging
import base64
import requests
import random
import urllib
import hashlib
import hmac
import re
import io
import xmlrpc.client
import http.client
import socket
import sys
from datetime import date, datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class BiSQLView(models.Model):
    _inherit = "bi.sql.view"

    # Field Selection
    execution_type = fields.Selection(
        selection=[
            ("sql", "SQL"),
            ("python", "Python"),
        ],
        string="Execution Type",
        default="sql",
        required=True,
        help="Choose between SQL query or Python code execution",
    )

    # Hot Update Logic Fields
    has_field_structure_change = fields.Boolean(
        string="Has Field Structure Change",
        compute="_compute_field_structure_change",
        store=False,
        help="Technical field to track if field structure has changed",
    )

    field_change_warning = fields.Text(
        string="Field Change Warning",
        compute="_compute_field_structure_change",
        store=False,
        help="Warning message when field structure changes",
    )

    view_order = fields.Char(
        default="list,pivot,graph",
    )

    # Override check execution enabled for Python
    _check_prohibited_words_enabled_python = False

    # Compute Section
    @api.depends("query", "execution_type")
    def _compute_field_structure_change(self):
        for rec in self:
            if rec.state in ("draft", "sql_valid"):
                rec.has_field_structure_change = False
                rec.field_change_warning = ""
                continue

            try:
                if rec.execution_type == "python":
                    result = rec._execute_python_request(for_check=True)
                else:
                    result = rec._execute_sql_request(mode="fetchall", header=True)

                if result:
                    field_changes = rec._check_field_changes(result)
                    rec.has_field_structure_change = field_changes["has_changes"]
                    rec.field_change_warning = field_changes["warning_message"]
                else:
                    rec.has_field_structure_change = False
                    rec.field_change_warning = ""
            except Exception as e:
                rec.has_field_structure_change = False
                rec.field_change_warning = ""

    # Override Section
    def write(self, vals):
        res = super(BiSQLView, self).write(vals)
        if "query" in vals and self.state in ("model_valid", "ui_valid"):
            # Trigger field structure change detection
            self._compute_field_structure_change()
        return res

    # Override validation method
    def button_validate_sql_expression(self):
        for item in self:
            if item.execution_type == "python":
                # For Python, skip prohibited words check
                if item._clean_query_enabled:
                    item._clean_query()
                if item._check_execution_enabled:
                    item._check_execution()
                item.state = "sql_valid"
            else:
                # For SQL, use original logic
                super(BiSQLView, item).button_validate_sql_expression()

    # Override execution check
    def _check_execution(self):
        self.ensure_one()
        if self.execution_type == "python":
            sql_view_field_obj = self.env["bi.sql.view.field"]
            result = self._execute_python_request(for_check=True)
            if not result or not isinstance(result, list):
                raise UserError(
                    _("Python code must return a list of dictionaries in variable 'result'.")
                )

            if not result:
                raise UserError(
                    _("No data returned from Python code.")
                )

            # Analyze result to create fields
            field_ids = []
            sample_row = result[0] if result else {}
            for idx, field_name in enumerate(sample_row.keys(), start=1):
                if not field_name.startswith("x_"):
                    continue

                existing_field = self.bi_sql_view_field_ids.filtered(
                    lambda x, name=field_name: x.name == name
                )
                
                # Determine field type from value
                field_type = self._get_python_field_type(sample_row[field_name])
                
                if existing_field:
                    field_ids.append(existing_field.id)
                    existing_field.write({
                        "sequence": idx,
                        "sql_type": field_type,
                    })
                else:
                    field_ids.append(
                        sql_view_field_obj.create({
                            "sequence": idx,
                            "name": field_name,
                            "sql_type": field_type,
                            "bi_sql_view_id": self.id,
                        }).id
                    )

            # Drop obsolete fields
            self.bi_sql_view_field_ids.filtered(
                lambda x: x.id not in field_ids
            ).unlink()

            if not self.bi_sql_view_field_ids:
                raise UserError(
                    _("No valid fields found. "
                      "Field names must be prefixed by 'x_'.")
                )

            return result
        else:
            # For SQL, use original logic
            return super(BiSQLView, self)._check_execution()

    # Override preview method
    def button_preview_sql_expression(self):
        self.button_validate_sql_expression()
        if self.execution_type == "python":
            res = self._execute_python_request()
        else:
            res = self._execute_sql_request()
        
        if isinstance(res, list):
            preview = res[:100]
            preview_text = "\n".join(map(lambda x: str(x), preview))
        else:
            preview_text = str(res)
        
        raise UserError(preview_text)

    # Python Execution Methods
    def _get_python_eval_context(self):
        """Provide eval context with available libraries"""
        self.ensure_one()
        
        def _dynamic_import(mod):
            modules_list = sys.modules
            if mod in modules_list:
                return sys.modules[mod]
            __import__(mod)
            return sys.modules[mod]

        return {
            '_dynamic_import': _dynamic_import,
            'mb': {
                're': re,
                'json': json,
                'random': random,
                'io': io,
                'hashlib': hashlib,
                'hmac': hmac,
                'urllib': urllib,
                'ast': ast,
                'requests': requests,
                'base64': base64,
                'xmlrpc.client': xmlrpc.client,
                'http.client': http.client,
                'socket': socket,
            },
            'env': self.env,
            'user': self.env.user,
            'result': None,  # Will be populated by user code
        }

    def _execute_python_request(self, for_check=False):
        """Execute Python code and return result"""
        self.ensure_one()
        if self.state == "draft" and not for_check:
            raise UserError(_("It is not allowed to execute a not checked request."))

        eval_context = self._get_python_eval_context()
        try:
            safe_eval(self.query, eval_context, mode="exec")
            result = eval_context.get('result')
            if result is None:
                raise UserError(_("Python code must assign result to variable 'result'."))
            if not isinstance(result, list):
                raise UserError(_("Variable 'result' must be a list of dictionaries."))
            if result and not all(isinstance(row, dict) for row in result):
                raise UserError(_("All items in 'result' must be dictionaries."))
            return result
        except Exception as e:
            _logger.exception("Python execution error")
            raise UserError(_("Python execution error:\n\n%s") % str(e)) from e

    def _get_python_field_type(self, value):
        """Determine field type from Python value"""
        if value is None:
            return "character varying"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "double precision"
        elif isinstance(value, str):
            return "character varying"
        else:
            return "character varying"

    # Hot Update Logic Methods
    def _check_field_changes(self, new_result):
        """Check if field structure has changed"""
        self.ensure_one()
        if not new_result:
            return {
                "has_changes": False,
                "new_fields": [],
                "removed_fields": [],
                "logic_only": True,
                "warning_message": "",
            }

        sample_row = new_result[0] if new_result else {}
        new_field_names = set(k for k in sample_row.keys() if k.startswith("x_"))
        existing_field_names = set(self.bi_sql_view_field_ids.mapped("name"))

        new_fields = new_field_names - existing_field_names
        removed_fields = existing_field_names - new_field_names
        has_changes = bool(new_fields or removed_fields)
        logic_only = not has_changes
        warning_parts = []
        if new_fields:
            warning_parts.append(_("New fields detected: %s") % ", ".join(sorted(new_fields)))
        if removed_fields:
            warning_parts.append(_("Removed fields detected: %s") % ", ".join(sorted(removed_fields)))
        warning_message = "\n".join(warning_parts) if warning_parts else ""

        return {
            "has_changes": has_changes,
            "new_fields": sorted(new_fields),
            "removed_fields": sorted(removed_fields),
            "logic_only": logic_only,
            "warning_message": warning_message,
        }

    def button_open_view(self):
        res = super().button_open_view()
        res.update({'name': self.name})
        return res

    def button_reset_for_new_fields(self):
        """Reset to sql_valid state when field structure changes"""
        for rec in self:
            if not rec.has_field_structure_change:
                raise UserError(_("No field structure changes detected."))
            # Reset to sql_valid state
            rec.button_reset_to_sql_valid()
            # Re-validate with new logic
            rec.button_validate_sql_expression()

    # Override prohibited words check for Python
    @property
    def _check_prohibited_words_enabled(self):
        self.ensure_one()
        return self.execution_type != "python"

    # Override view creation methods for Python
    def _prepare_request_check_execution(self):
        self.ensure_one()
        if self.execution_type == 'python':
            # For Python, we don't need to prepare request
            return None
        return super(BiSQLView, self)._prepare_request_check_execution()

    def _prepare_request_for_execution(self):
        self.ensure_one()
        if self.execution_type == 'python':
            # For Python, we don't need to prepare request
            return None
        return super(BiSQLView, self)._prepare_request_for_execution()

    def _create_view_from_python(self):
        """Create view from Python execution result"""
        self.ensure_one()
        # Execute Python code to get data
        result = self._execute_python_request()

        if not result:
            raise UserError(_("No data returned from Python code."))

        # Get field names and types
        fields = self.bi_sql_view_field_ids.sorted('sequence')
        field_names = [f.name for f in fields]

        # Create temporary table with data
        temp_table = f"temp_{self.view_name}"
        # Drop view first (if exists) since it depends on the temp table
        self._log_execute(f"DROP VIEW IF EXISTS {self.view_name}")
        self._log_execute(f"DROP TABLE IF EXISTS {temp_table}")

        # Create table structure
        col_defs = []
        for field in fields:
            col_defs.append(f"{field.name} {self._get_sql_type_from_field_type(field.sql_type)}")

        create_table_sql = f"CREATE TABLE {temp_table} (id SERIAL PRIMARY KEY, {', '.join(col_defs)})"
        self._log_execute(create_table_sql)

        # Insert data
        for row in result:
            values = []
            for field_name in field_names:
                value = row.get(field_name)
                if value is None:
                    values.append('NULL')
                elif isinstance(value, str):
                    escaped_value = value.replace("'", "''")
                    values.append(f"'{escaped_value}'")
                elif isinstance(value, bool):
                    values.append('TRUE' if value else 'FALSE')
                elif isinstance(value, (datetime, date, time)):
                    values.append(f"'{value}'")
                else:
                    values.append(str(value))
            insert_sql = f"INSERT INTO {temp_table} ({', '.join(field_names)}) VALUES ({', '.join(values)})"
            self._log_execute(insert_sql)

        # Create view from temporary table
        create_view_sql = f"""
            CREATE VIEW {self.view_name} AS
            SELECT
                row_number() OVER () as id,
                NULL as create_date,
                NULL as create_uid,
                NULL as write_date,
                NULL as write_uid,
                {', '.join(field_names)}
            FROM {temp_table}
        """
        self._log_execute(create_view_sql)

    def _get_sql_type_from_field_type(self, field_type):
        """Convert field type to database type"""
        type_mapping = {
            'character varying': 'VARCHAR',
            'text': 'TEXT',
            'integer': 'INTEGER',
            'double precision': 'DOUBLE PRECISION',
            'boolean': 'BOOLEAN',
            'date': 'DATE',
            'timestamp without time zone': 'TIMESTAMP',
        }
        return type_mapping.get(field_type, 'VARCHAR')

    def _create_view(self):
        for sql_view in self:
            if sql_view.execution_type == 'python':
                # For Python, skip view creation (handled separately)
                continue
            super(BiSQLView, sql_view)._create_view()

    def _drop_view(self):
        for sql_view in self:
            if sql_view.execution_type == 'python':
                # For Python, skip view dropping
                continue
            super(BiSQLView, sql_view)._drop_view()

    def _refresh_materialized_view(self):
        for sql_view in self:
            if sql_view.execution_type == 'python':
                # For Python, re-create view from Python execution
                sql_view._create_view_from_python()
                continue
            super(BiSQLView, sql_view)._refresh_materialized_view()

    def button_create_sql_view_and_model(self):
        for sql_view in self.filtered(lambda x: x.state == "sql_valid"):
            # Check if many2one fields are correctly
            bad_fields = sql_view.bi_sql_view_field_ids.filtered(
                lambda x: x.ttype == "many2one" and not x.many2one_model_id.id
            )
            if bad_fields:
                raise ValidationError(
                    _("Please set related models on the following fields %s")
                    % ",".join(bad_fields.mapped("name"))
                )
            # Create ORM and access
            sql_view._create_model_and_fields()
            sql_view._create_model_access()

            # Create View and indexes
            if sql_view.execution_type == 'python':
                # For Python, create view from Python execution result
                sql_view._create_view_from_python()
            else:
                sql_view._create_view()
                sql_view._create_index()

            # Create cron job for materialized views (both SQL and Python)
            if sql_view.is_materialized:
                if not sql_view.cron_id:
                    sql_view.cron_id = (
                        self.env["ir.cron"].create(sql_view._prepare_cron()).id
                    )
                else:
                    sql_view.cron_id.active = True
            sql_view.state = "model_valid"
