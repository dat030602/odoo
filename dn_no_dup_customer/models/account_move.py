from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    dn_name_dup_id = fields.Many2one('res.partner', string="Duplicate Warning", related='partner_id.dn_name_dup_id')
    dn_email_dup_id = fields.Many2one('res.partner', string="Duplicate Warning", related='partner_id.dn_email_dup_id')
    dn_phone_dup_id = fields.Many2one('res.partner', string="Duplicate Warning", related='partner_id.dn_phone_dup_id')
    dn_phone_mobile_search_dup_id = fields.Many2one('res.partner', string="Duplicate Warning", related='partner_id.dn_phone_mobile_search_dup_id')
    