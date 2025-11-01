# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    default_viettel_sinvoice_template_id = fields.Many2one('viettel.sinvoice.template', string='Default S-Invoice Template')
