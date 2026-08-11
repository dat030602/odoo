# -*- coding: utf-8 -*-
"""
ir_actions_server.py
====================

Extension of ir.actions.server to add a new action state:
'Generate Excel From Template'.

This allows users to configure Excel report generation through the
Odoo UI (Settings → Technical → Actions → Server Actions) without
creating a dedicated child module.

The Python code field is used to build the report context dict, which
is then passed to TemplateEngine via base.excel.report._generate_from_attachment().
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    state = fields.Selection(
        selection_add=[('excel_template', 'Generate Excel From Template')],
        ondelete={'excel_template': 'cascade'},
    )
    excel_template_name = fields.Char(
        string='Excel Template Name',
        help="Name of the Excel template file in Attachments "
             "with 'Is Excel Template' checked.",
    )
    excel_template_attachment = fields.Binary(
        string='Excel Template',
        help="Template file uploaded to Attachments with "
             "'Is Excel Template' checked.",
    )

    # ------------------------------------------------------------------ #
    # Odoo 19 uses a non-blocking warning banner (_get_warning_messages /
    # _compute_warning) for action misconfiguration instead of a hard
    # ValidationError constraint. Follow that convention here rather than
    # @api.constrains, so an incomplete action can still be saved as a
    # draft and only fails when actually Run.
    # ------------------------------------------------------------------ #
    def _warning_depends(self):
        return super()._warning_depends() + ['excel_template_attachment']

    def _get_warning_messages(self):
        warnings = super()._get_warning_messages()
        if self.state == 'excel_template' and not self.excel_template_attachment:
            warnings.append(_(
                "Select an Excel template when using "
                "'Generate Excel From Template'."
            ))
        return warnings

    # ------------------------------------------------------------------ #
    # Dispatch target. Odoo's _get_runner() looks up
    # `_run_action_{state}_multi` first (falls back to the non-multi
    # variant if absent). The `_multi` suffix means this method receives
    # ALL selected records in `eval_context['records']` in a single call
    # instead of being invoked once per record — required here so that a
    # multi-select in a list view produces ONE Excel file, not one per row.
    # ------------------------------------------------------------------ #
    def _run_action_excel_template_multi(self, eval_context=None):
        self.ensure_one()
        if not self.excel_template_attachment:
            raise UserError(_(
                "No Excel template selected for this server action."
            ))

        # `code` carries the same protection as the built-in 'Execute
        # Code' state: field-level `groups='base.group_system'` plus
        # Odoo 19's automatic ir.actions.server.history versioning on
        # every write() to this field (see Section 15.9).
        safe_eval(
            self.sudo().code.strip(), eval_context,
            mode='exec', filename=str(self),
        )
        report_context = eval_context.get('excel_context')
        if not isinstance(report_context, dict):
            raise UserError(_(
                "The Python code must set a variable named "
                "'excel_context' to a dict. Available variables: env, "
                "model, record, records (see the code editor's help tab)."
            ))

        wizard = self.env['base.excel.report'].create({})
        return wizard._generate_from_attachment(self.excel_template_name, self.excel_template_attachment, report_context)
