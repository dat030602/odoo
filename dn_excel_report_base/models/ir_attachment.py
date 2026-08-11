# -*- coding: utf-8 -*-
"""
ir_attachment.py
================

Extension of ir.attachment to mark Excel template files.

This allows the Server Action integration (Section 14) to filter
attachments that are valid Excel templates for the
'Generate Excel From Template' action.
"""

from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    is_excel_template = fields.Boolean(
        string='Is Excel Template',
        help="Marks this attachment as selectable in the "
             "'Generate Excel From Template' server action.",
    )
