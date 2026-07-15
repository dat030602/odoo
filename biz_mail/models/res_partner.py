from odoo import api, fields, models, tools, _
from odoo.osv import expression
import pprint



class ResUsers(models.Model):
    _inherit = 'res.partner'
    _description = 'Res Partner'


    @api.model
    def get_mention_suggestions(self, search, limit=8, channel_id=None):
        values = super().get_mention_suggestions(search, limit, channel_id=channel_id)
        
        all_user_id = self.env.ref('biz_mail.all_user')
        if all_user_id and all_user_id.partner_id:
            partner_format = all_user_id.partner_id.all_mail_partner_format()
            if channel_id:
                # member_by_partner = {member.partner_id: member for member in self.env['mail.channel.member'].search([('channel_id', '=', channel_id), ('partner_id', 'in', partners.ids)])}
                partner_format.get(all_user_id.partner_id)['persona'] = {'channelMembers': [('insert',
                                  {'channel': {'id': channel_id},
                                   'id': False,
                                   'persona': {'partner': {'id': all_user_id.partner_id.id}}})]}
            print("partner_format", partner_format)
            
            values += list(partner_format.values())

        return values

    def all_mail_partner_format(self, fields=None):
        partners_format = dict()
        if not fields:
            fields = {'id': True, 'name': True, 'email': True, 'active': True, 'im_status': True, 'user': {}}
        for partner in self:
            data = {}
            if 'id' in fields:
                data['id'] = partner.id
            if 'name' in fields:
                data['name'] = partner.name
            if 'email' in fields:
                data['email'] = partner.email
            if 'active' in fields:
                data['active'] = True
            if 'im_status' in fields:
                data['im_status'] = 'online'
            if 'user' in fields:
                main_user = self.env.ref('biz_mail.all_user')

                data['user'] = {
                    "id": main_user.id,
                    "isInternalUser": not main_user.share,
                } if main_user else [('clear',)]
            
            partners_format[partner] = data
        return partners_format


    # @api.model
    # def get_mention_suggestions(self, search, limit=8, channel_id=None):
    #     """ Return 'limit'-first partners' such that the name or email matches a 'search' string.
    #         Prioritize partners that are also users, and then extend the research to all partners.
    #         If channel_id is given, only members of this channel are returned.
    #         The return format is a list of partner data (as per returned by `mail_partner_format()`).
    #     """
    #     search_dom = expression.OR([[('name', 'ilike', search)], [('email', 'ilike', search)]])
    #     search_dom = expression.AND([[('active', '=', True), ('type', '!=', 'private')], search_dom])
    #     if channel_id:
    #         search_dom = expression.AND([[('channel_ids', 'in', channel_id)], search_dom])

    #     # Search partners that are also users
    #     domain = expression.AND([[('user_ids.id', '!=', False), ('user_ids.active', '=', True)], search_dom])
    #     partners = self.search(domain, limit=limit)

    #     # Search partners that are not users if less than 'limit' partner that are users found
    #     remaining_limit = limit - len(partners)
    #     if remaining_limit > 0:
    #         partners |= self.search(expression.AND([[('id', 'not in', partners.ids)], search_dom]), limit=remaining_limit)

    #     list_partners = list(partners.mail_partner_format().values())
    #     vals = {
    #         'id': False,
    #         'display_name': 'All',
    #         'name': 'All',
    #         'email': '@all',
    #         'active': True,
    #         'im_status': False,
    #         'user_id': False,
    #         'is_internal_user': True
    #     }
    #     list_partners.append(vals)
    #     print("list_partners------>>>", list_partners)

    #     return list_partners

    # @api.model
    # def search_for_channel_invite(self, search_term, channel_id=None, limit=30):
    #     """ Returns partners matching search_term that can be invited to a channel.
    #     If the channel_id is specified, only partners that can actually be invited to the channel
    #     are returned (not already members, and in accordance to the channel configuration).
    #     """
    #     domain = expression.AND([
    #         expression.OR([
    #             [('name', 'ilike', search_term)],
    #             [('email', 'ilike', search_term)],
    #         ]),
    #         [('active', '=', True)],
    #         [('type', '!=', 'private')],
    #         [('user_ids', '!=', False)],
    #         [('user_ids.active', '=', True)],
    #         [('user_ids.share', '=', False)],
    #     ])
    #     if channel_id:
    #         channel = self.env['mail.channel'].search([('id', '=', int(channel_id))])
    #         domain = expression.AND([domain, [('channel_ids', 'not in', channel.id)]])
    #         if channel.group_public_id:
    #             domain = expression.AND([domain, [('user_ids.groups_id', 'in', channel.group_public_id.id)]])
    #     query = self.env['res.partner']._search(domain, order='name, id')
    #     query.order = 'LOWER("res_partner"."name"), "res_partner"."id"'  # bypass lack of support for case insensitive order in search()
    #     query.limit = int(limit)
    #     return {
    #         'count': self.env['res.partner'].search_count(domain),
    #         'partners': list(self.env['res.partner'].browse(query).mail_partner_format().values()),
    #     }



    # @api.model
    # def search_for_user_forward(self, search_term, channel_id=None):
    #     print("demo demo demo...............")
    #     if channel_id:
    #         partner_ids = self.env['mail.channel'].browse(channel_id).mapped('channel_partner_ids')
    #         if partner_ids:
    #             if search_term:
    #                 partner_ids = self.env['res.partner'].search([('name', 'ilike', search_term), ('id', 'in', partner_ids.ids)])
                
    #             if self.env.user.partner_id in partner_ids:
    #                 partner_ids -= self.env.user.partner_id

    #         return {
    #             'partners': list(partner_ids.mail_partner_format().values()),
    #         }

    @api.model
    def search_for_user_forward(self, search_term, channel_id=None):
        
        domain = expression.AND([
            expression.OR([
                [('name', 'ilike', search_term)],
                [('email', 'ilike', search_term)],
            ]),
            [('active', '=', True)],
            [('type', '!=', 'private')],
            [('user_ids', '!=', False)],
            [('user_ids.active', '=', True)],
            [('user_ids.share', '=', False)],
            
        ])
        
        current_parnter = self.env.user.partner_id
        if current_parnter:
            domain += expression.AND([
                [('id', 'not in', current_parnter.ids)]
            ])
        # if channel_id:
        #     channel = self.env['mail.channel'].search([('id', '=', int(channel_id))])
        #     partner_ids = channel.mapped('channel_member_ids.partner_id')
        #     if current_parnter in partner_ids:
        #         partner_ids -= current_parnter

        #     domain += expression.AND([
        #         [('id', 'in', partner_ids.ids)]
        #     ])
        #     if channel.group_public_id:
        #         domain = expression.AND([domain, [('user_ids.groups_id', 'in', channel.group_public_id.id)]])

        query = self.env['res.partner']._search(domain, order='name, id')
        query.order = 'LOWER("res_partner"."name"), "res_partner"."id"' 
        result = {
            'partners': list(self.env['res.partner'].browse(query).mail_partner_format().values()),
        }
        
        return result