from odoo import api, fields, models,_

class Users(models.Model):
    _inherit = "res.users"

    type_contact_user_ids = fields.Many2many('res.partner.account',string='Type Contact')


    def _cron_update_address_type(self):
        partner_ids = self.search([('partner_id','!=',False),'|',('active','!=',False),('active','=',False)])
        
        if partner_ids:
            partner_ids.write({
                'type': 'contact',
                'is_user_contact': True

            })
    
    @api.model_create_multi
    def create(self, vals_list):
        """ Automatically subscribe employee users to default digest if activated """
        users = super(Users, self).create(vals_list)
        partner_ids = users.filtered(lambda u: u.partner_id)
        if partner_ids:
            partner_ids.write({
                'is_user_contact': True
            })

        return users



    
