from odoo import api, fields, models, tools, _



class ResUsers(models.Model):
    _inherit = 'res.users'
    _description = 'Res Users'

    is_hide_menu_chat = fields.Boolean(string="Is hide menu chat", default=False)
    is_admin_all_channel = fields.Boolean(string="Is admin all channel", default=False)

    def write(self, values):
        # remove_permissions = add_permissions = self.env['res.users']
        # old_users = {user.id: True for user in self if user.has_group('biz_mail.group_all_channel')}
        # channel_ids = self.env['mail.channel'].sudo().search([('channel_type', '=', 'channel')])
        # group_ids = self.env.ref('biz_mail.group_all_channel')

        if 'is_hide_menu_chat' in values:
            module_mail = self.env['ir.ui.menu'].search([('action', '!=', False)]).filtered(
                lambda x: x.action.xml_id == 'mail.action_discuss')
            group_hide_menu = self.env.ref('biz_mail.group_hidden_menu_chat')
            if values.get('is_hide_menu_chat'):
                if module_mail:
                    values['hide_menu_access_ids'] = [(4, module_mail.id)]
                if group_hide_menu:
                    field = f"in_group_{group_hide_menu.id}"
                    values[field] = True
            else:
                if module_mail:
                    values['hide_menu_access_ids'] = [(3, module_mail.id)]
                if group_hide_menu:
                    field = f"in_group_{group_hide_menu.id}"
                    values[field] = False

        if "is_admin_all_channel" in values:
            group_admin_all_channel = self.env.ref('biz_mail.group_admin_all_channel')
            if values.get("is_admin_all_channel"):
                if group_admin_all_channel:
                    field = f"in_group_{group_admin_all_channel.id}"
                    values[field] = True
            else:
                if group_admin_all_channel:
                    field = f"in_group_{group_admin_all_channel.id}"
                    values[field] = False

        result = super(ResUsers, self).write(values)
        # after change
        # for user in self:
        #     if old_users.get(user.id) and not user.has_group('biz_mail.group_all_channel'):
        #         remove_permissions += user
        #     if not old_users.get(user.id) and user.has_group('biz_mail.group_all_channel'):
        #         add_permissions += user
        #
        # if remove_permissions:
        #     channel_ids._remove_members(remove_permissions)
        # if add_permissions:
        #     channel_ids._subscribe_users(group_ids)

        return result

    @api.model_create_multi
    def create(self, vals_list):
        '''
            All channels add this user if the user has all channel permission
        '''
        users = super(ResUsers, self).create(vals_list)
        # for user in users:
        #     if user.has_group('biz_mail.group_all_channel'):
        #         channel_ids = self.env['mail.channel'].sudo().search([('channel_type', '=', 'channel')])
        #         group_ids = self.env.ref('biz_mail.group_all_channel')
        #         channel_ids._subscribe_users(group_ids)
                
        return users

    