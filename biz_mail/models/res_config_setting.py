import datetime

from odoo import api, fields, models, tools


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    user_id = fields.Many2one('res.users', string='Main Admin', config_parameter='user_id',\
         domain=lambda self: "[('groups_id', 'in', %s)]"% self.env.ref('base.group_user').id)


    def set_values(self):
        channels = self.env['mail.channel'].sudo().search([('channel_type', '=', 'channel')])
        channels.sudo().write({'main_user_id': self.user_id and self.user_id.id or False})
        old_user_id = self.env["ir.config_parameter"].sudo().get_param("user_id")
        new_user_id = self.user_id
        if old_user_id == new_user_id.id:
            pass
        else:
            if old_user_id:
                old_user_id = self.env["res.users"].browse(int(old_user_id)).exists()
                old_user_id.update({"is_admin_all_channel": False})
            if new_user_id:
                new_user_id.update({"is_admin_all_channel": True})

        return super(ResConfigSettings, self).set_values()
        