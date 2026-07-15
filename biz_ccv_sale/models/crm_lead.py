# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import random

from odoo import api, fields, models, _
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.tools import html_escape
from odoo.exceptions import UserError, ValidationError



class CrmLead(models.Model):
    _inherit = "crm.lead"

    code_contact = fields.Char(related="partner_id.code_contact",string='Contact Code', readonly=False, required=True)

    # @api.onchange('code_contact')
    # def onchange_code_contact(self):
    #     if not self.partner_id:
    #         raise ValidationError("Please select a partner first.")




