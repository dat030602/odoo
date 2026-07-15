# -*- coding: utf-8 -*-
from odoo import fields, models

class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    archive_user = fields.Boolean(string='Archive User',default=True)
    archive_partner = fields.Boolean(string='Archive Partner',default=True)

    def action_register_departure(self):
        res =  super(HrDepartureWizard, self).action_register_departure()
        context = self.env.context.copy()

        employee_id =self.env['hr.employee'].browse(context['active_id'])

        # Employee Related User Archive 
        if self.archive_user and employee_id.user_id:
            employee_id.user_id.sudo().active = False
        
        # Employee Related Partner(Contact) Archive 
        if self.archive_partner and employee_id.user_id and employee_id.user_id.partner_id:
            employee_id.user_id.partner_id.sudo().active = False
        
        # Employee Related Partner(Contact) Not Archive
        # But, Employee => User => Partner(Contact) Archive
        if self.archive_partner and employee_id.related_contact_ids or employee_id.address_home_id:
            partner = employee_id.related_contact_ids | employee_id.address_home_id
            [setattr (rec,'active', False) for rec in partner]
        return res