# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo import api, fields, models, _


class WarehouseSummaryByCostWizard(models.TransientModel):
    _name = 'warehouse.summary.by.cost.wizard'
    _description = 'WarehouseSummaryByCostWizard'

    date_from = fields.Date('Date From',required=True)
    date_to = fields.Date('Date To',required=True)


