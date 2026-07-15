from odoo import fields, models, api, exceptions 

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    note = fields.Text('Note')
    creator_id = fields.Many2one('res.users', string="Creator")
    chief_accountant_id = fields.Many2one('res.users', string="Chief Accountant")
    unit_head_id = fields.Many2one('res.users', string="Head Unit")
    number_ctnb = fields.Char('Number CTNB')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('number_ctnb'):
                vals['number_ctnb'] = sequence = self.env['ir.sequence'].next_by_code('account.payment.CTNB')
        return super(AccountPayment, self).create(vals_list)
