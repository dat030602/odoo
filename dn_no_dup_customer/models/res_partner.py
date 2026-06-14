from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    dn_name_dup_id = fields.Many2one('res.partner', string="Duplicate Warning", compute="_compute_duplicate_message")
    dn_email_dup_id = fields.Many2one('res.partner', string="Duplicate Warning", compute="_compute_duplicate_message")
    dn_phone_dup_id = fields.Many2one('res.partner', string="Duplicate Warning", compute="_compute_duplicate_message")
    dn_phone_mobile_search_dup_id = fields.Many2one('res.partner', string="Duplicate Warning", compute="_compute_duplicate_message")

    @api.depends('name', 'email', 'phone', 'phone_mobile_search')
    def _compute_duplicate_message(self):
        for record in self:
            record.dn_name_dup_id = False
            record.dn_email_dup_id = False
            record.dn_phone_dup_id = False
            record.dn_phone_mobile_search_dup_id = False

            if record.name:
                duplicate_name_ids = self.search([('id', '!=', record.id), ('name', '=', record.name)])
                record.dn_name_dup_id = duplicate_name_ids[0] if duplicate_name_ids else False

            if record.email:
                duplicate_email_ids = self.search([('id', '!=', record.id), ('email', '=', record.email)])
                record.dn_email_dup_id = duplicate_email_ids[0] if duplicate_email_ids else False

            if record.phone:
                duplicate_phone_ids = self.search([('id', '!=', record.id), ('phone', '=', record.phone)])
                record.dn_phone_dup_id = duplicate_phone_ids[0] if duplicate_phone_ids else False

            if record.phone_mobile_search:
                duplicate_mobile_ids = self.search([('id', '!=', record.id), ('phone_mobile_search', '=', record.phone_mobile_search)])
                record.dn_phone_mobile_search_dup_id = duplicate_mobile_ids[0] if duplicate_mobile_ids else False



            
