# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    chief_commerce_department_id = fields.Many2one('res.users', config_parameter='ccv_sql.chief_commerce_department_id', string="Phòng Thương mại")
    chief_business_department_id = fields.Many2one('res.users', config_parameter='ccv_sql.chief_business_department_id', string="Phòng Kinh doanh")
    chief_accountant_id = fields.Many2one('res.users', config_parameter='ccv_sql.chief_accountant_id', string="Kế toán trưởng")
    cashier_accountant_id = fields.Many2one('res.users', config_parameter='ccv_sql.cashier_accountant_id', string="Kế toán thủ quỹ")
    unit_head_id = fields.Many2one('res.users', config_parameter='ccv_sql.unit_head_id', string="Thủ trưởng đơn vị")
    debt_accountant_id = fields.Many2one('res.users', config_parameter='ccv_sql.debt_accountant_id', string="Kế toán công nợ")