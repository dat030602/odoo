from dataclasses import field
from email.policy import default
from odoo import api, fields, models, tools, Command, _
from odoo.exceptions import ValidationError
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pprint

import logging
import re

_logger = logging.getLogger(__name__)
from .common import convert_datetime

        
class MailChannel(models.Model):
    _inherit = 'mail.channel'
    _description = 'Mail Channel'


    # @api.model
    # def _default_groups_ids(self):
    #     res = []
    #     group_all_channel_id = self.env['ir.model.data']._xmlid_to_res_id(
    #         'biz_mail.group_all_channel', raise_if_not_found=False)
    #     ctx = self._context
    #
    #     if group_all_channel_id and not ctx.get('channel_type'):
    #         res.append(group_all_channel_id)
    #     return res

    def _default_main_user_id(self):
        params = self.env['ir.config_parameter'].sudo()
        user_id = params.get_param('user_id')
        return user_id and int(user_id) or False

    # overide
    # group_ids = fields.Many2many(default=_default_groups_ids)
    main_user_id = fields.Many2one('res.users', string='Main Admin', default=_default_main_user_id, readonly=True,\
                                        domain=lambda self: "[('groups_id', 'in', %s)]"% self.env.ref('base.group_user').id)
    sub_user_id = fields.Many2many('res.users', string='Sub Admin', default=lambda self: [self.env.user.id], \
                                        domain=lambda self: "[('groups_id', 'in', %s)]"% self.env.ref('base.group_user').id)
    is_edit_sub_user = fields.Boolean("Is Edit Sub Admin", 
        compute='_compute_edit_sub_user')
    
    members_seen_channel = fields.Many2many('res.partner')
    last_message_seen_id = fields.Integer('Last Message Seen ID')
    show_read = fields.Boolean('Show Read')
    is_pinned_channel = fields.Boolean('Is Pinned Channel?')
    no_pinned_channel = fields.Integer(default=0)
    check_notification_channel = fields.Boolean('Notification Channel')
    # WARNING
    partner_seen_channel_ids = fields.One2many('partner.seen.channel', 'channel_id')

    @api.model_create_multi
    def create(self, vals_list):
        for idx,vals in enumerate(vals_list, 0):
            if vals.get('channel_type', False) and vals['channel_type'] in ('chat', 'group'):
                self = self.with_context(channel_type=True)
               
        return super(MailChannel, self).create(vals_list)
    
    def write(self, vals):
        current_user = self.env.user
        old_members_dict = {channel.id: channel.channel_member_ids for channel in self}
        result = super(MailChannel, self).write(vals)
        for channel_id in self:
            remove_members = add_memmbers = self.env['mail.channel']
            new_membes = channel_id.channel_member_ids
            remove_members = old_members_dict.get(channel_id.id) - new_membes
            add_memmbers = new_membes - old_members_dict.get(channel_id.id)
            allowed_users = channel_id.main_user_id | channel_id.sub_user_id
            
            if not current_user.has_group('base.group_system') and current_user not in allowed_users and (remove_members or add_memmbers):
                raise ValidationError(_('You are not allowed to add/delete members in this channel !!!, Please contact channel owner %s.')%(channel_id.main_user_id.name if channel_id.main_user_id else ''))

        return result

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, message_type='notification', **kwargs):
        """
        PROJECT: CCV
        Task ID: 18299
        """
        allowed_user = self.main_user_id | self.sub_user_id
        if self.check_notification_channel and self.env.user not in allowed_user:
            raise ValidationError(_('Channel %s was lock by user admin' % (self.name)))
        return super(MailChannel, self).message_post(message_type=message_type ,**kwargs)
    
    
    @api.depends('main_user_id')
    def _compute_edit_sub_user(self):
        for record in self:
            record.is_edit_sub_user = False
            if self.env.user == record.main_user_id:
                record.is_edit_sub_user = True
    
    @api.onchange('show_read')
    def onchange_show_read(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'} 

    def _subscribe_users(self, group_ids):
        new_members = self._subscribe_users_get_members(group_ids)
        if new_members:
            to_create = [
                {'channel_id': channel_id, 'partner_id': partner_id}
                for channel_id in new_members
                for partner_id in new_members[channel_id]
            ]
            self.env['mail.channel.member'].sudo().create(to_create)
    
    def _subscribe_users_get_members(self, group_ids):
        """ Return new members per channel ID """
        if self._context.get("has_partner"):
            return dict(
                (channel.id, (self._context.get("has_partner")).ids)
                for channel in self
            )
        return dict(
            (channel.id, (group_ids.users.partner_id - channel.channel_partner_ids).ids)
            for channel in self
        )

    def _remove_members(self, users):
        for channel in self:
            member_ids = self.env['mail.channel.member'].sudo().search([
                ('partner_id', 'in', users.mapped('partner_id').ids),
                ('channel_id', '=', channel.id)
            ])
            
            if member_ids:
                member_ids.unlink()

    def add_members(self, partner_ids=None, guest_ids=None, invite_to_rtc_call=False, open_chat_window=False, post_joined_message=True):
        current_user = self.env.user
        allowed_users = self.main_user_id | self.sub_user_id
    
        if not current_user.has_group('base.group_system') and current_user not in allowed_users:
            raise ValidationError(_('You are not allowed to add/delete members in this channel !!!, Please contact channel owner %s.')%(self.main_user_id.name if self.main_user_id else ''))

        super(MailChannel, self).add_members(partner_ids=partner_ids, 
                    guest_ids=guest_ids, invite_to_rtc_call=invite_to_rtc_call, 
                    open_chat_window=open_chat_window, post_joined_message=post_joined_message)
    
    ########################################################################################
    

    def _get_channel_last_seen_partner_ids(self, send_to_partner, channel):
        partner_ids = []
        from_partner = self.env['mail.channel.partner'].create({
            'is_pinned':True,
            'channel_id': channel.id,
            'partner_id': self.env.user.partner_id.id
        })
        partner_ids.append(from_partner.id)
        to_partner = self.env['mail.channel.partner'].create({
            'is_pinned':True,
            'channel_id': channel.id,
            'partner_id': send_to_partner
        })
        partner_ids.append(to_partner.id)
        return [(6, 0, partner_ids)]

    
    @api.model
    def send_message_to_user(self, send_to_partner, send_content, message_id, author_name, message_date):
        result = {'success': False}
        channel = self.search([
            ('channel_type', '=', 'chat'),
            ('channel_last_seen_partner_ids', 'in', self.env['mail.channel.partner'].sudo()._search([
                ('partner_id', '=', send_to_partner),
                ('is_pinned', '=', True),
            ])),
        ], limit=1)
        
        if not channel:
            # create a new one
            channel = self.create({
                'public': 'private',
                'channel_type': 'chat',
                'name': ', '.join(self.env['res.partner'].sudo().browse(send_to_partner).mapped('name')),
            })
            channel.channel_last_seen_partner_ids = [(6, 0, [])]
            channel.write({
                'channel_last_seen_partner_ids': self._get_channel_last_seen_partner_ids(send_to_partner, channel),
            })
            channel._broadcast(send_to_partner)
        
        result = self._send_action(channel.id, message_id, send_content, author_name, message_date)
        result['channel_id'] =  channel.id
        
        return result

    @api.model
    def send_message_to_channel(self, send_to_channel, send_content, message_id, author_name, message_date):
        result = {'success': False}
        if send_to_channel:
           result = self._send_action(send_to_channel, message_id, send_content, author_name, message_date)

        return result
    

    # --------- From js ---------------- #

    def _get_body_content(self, message, typed_message, author_name, message_date):
        sub_mes = ""
        str_author = ""
        if author_name:
            str_author = """
                <div style="display: inline; padding-left: 11px; padding-right: 12px; padding-top: 9px;
                    margin-top: 0px; margin-bottom: 12px; font-family: &quot;SF Regular&quot;, &quot;Segoe System UI Regular&quot;, &quot;Segoe UI Regular&quot;, sans-serif;
                    font-weight: 400; color: rgb(138, 141, 145); font-size: 12px;">
                        %s, %s
                </div> 
        """ % (author_name, message_date)
        if typed_message:
            sub_mes = """
                    <div style="position: relative; display: flex; border-style: solid; border-width: 0px 0px 1px;
                        margin-bottom: 14px; border-color: rgb(138, 141, 145);">
                    </div>
                    <div><p>%s</p></div>
                  
                    
                """ % (typed_message)
        
            result = """
                <div style="background-color: rgb(219, 241, 255); padding-left: 11px; padding-right: 12px; padding-top: 9px; border-radius: 18px;">
                    <span class="otro-blockquote"></span>
                    <div class="biz-message" style="border-radius: 10px 10px 0px; background-color: rgb(219, 241, 255); display: flex;
                        padding-left: 11px; padding-right: 12px;padding-top: 9px;">%s
                    </div>
                    %s%s
                </div>
            
                """ % (message, str_author, sub_mes)
        else:
            result = """
                <div style="background-color: rgb(219, 241, 255); padding-left: 11px; padding-right: 12px; padding-top: 9px; border-radius: 18px;">
                    <span class="otro-blockquote"></span>
                    <div class="biz-message" style="border-radius: 10px 10px 0px; background-color: rgb(219, 241, 255); display: flex;
                        padding-left: 11px; padding-right: 12px;padding-top: 9px;">%s
                    </div>
                    %s
                </div>
                """ % (message, str_author)
            
        return result
    
    def _get_value(self, forward_message):
        value = {
            'success': True,
            'message_id': forward_message.id,
            'body': forward_message.body,
            'attachment_ids': forward_message.attachment_ids.ids
        }
        forward_message.unlink()
        return value

    def _send_action(self, message_id, 
                    content, author_name,
                    message_date, to_channel):

        result = {'success': False}
        MailMessage = self.env['mail.message']
        mail_message = MailMessage.browse(int(message_id))
        
        if mail_message:
            forward_message = mail_message.copy()
            if not forward_message.is_forward:
                body = self._get_body_content(forward_message.body, content, author_name, message_date)
                forward_message.body = body
            author_id, email_from = self.env['mail.thread']._message_compute_author(self.env.user.partner_id.id, email_from=None, raise_on_email=False)
            forward_message.author_id = author_id
            forward_message.email_from = email_from
            forward_message.is_forward = True
            forward_message.res_id = to_channel
            forward_message.date = fields.Datetime.now()
            
            return self._get_value(forward_message)

        forward_message = MailMessage.create({
            'model': 'mail.channel',
            'res_id': to_channel.id,
            'body': body,
            'author_id': self.env.user.partner_id.id,
            'is_forward': True
        })
        return self._get_value(forward_message)
        
    @api.model
    def send_message_to_channel(self, message_id, 
                    content, author_name,
                    message_date, to_channel):
        
        result = {'success': False}
        if to_channel:
            result = self._send_action(message_id, content, author_name, message_date, to_channel)

        return result
    
    @api.model
    def send_message_to_user(self, message_id, 
                    content, author_name,
                    message_date, to_partner):
        

        partners_to = self.env.user.partner_id.ids + [to_partner]
        self.flush_model()
        self.env['mail.channel.member'].flush_model()
        self.env.cr.execute("""
            SELECT M.channel_id
            FROM mail_channel C, mail_channel_member M
            WHERE M.channel_id = C.id
                AND M.partner_id IN %s
                AND C.channel_type LIKE 'chat'
                AND NOT EXISTS (
                    SELECT 1
                    FROM mail_channel_member M2
                    WHERE M2.channel_id = C.id
                        AND M2.partner_id NOT IN %s
                )
            GROUP BY M.channel_id
            HAVING ARRAY_AGG(DISTINCT M.partner_id ORDER BY M.partner_id) = %s
            LIMIT 1
        """, (tuple(partners_to), tuple(partners_to), sorted(list(partners_to)),))
        result = self.env.cr.dictfetchall()

        if result:
            # get the existing channel between the given partners
            channel = self.browse(result[0].get('channel_id'))
            # pin up the channel for the current partner
            self.env['mail.channel.member'].search([('partner_id', '=', self.env.user.partner_id.id), ('channel_id', '=', channel.id)]).write({
                'is_pinned': True,
                'last_interest_dt': fields.Datetime.now(),
            })
            channel._broadcast(self.env.user.partner_id.ids)

        if not result:
            channel = self.create({
                'channel_partner_ids': [Command.link(partner_id) for partner_id in partners_to],
                'channel_member_ids': [
                    Command.create({
                        'partner_id': partner_id,
                        # only pin for the current user, so the chat does not show up for the correspondent until a message has been sent
                        'is_pinned': partner_id == self.env.user.partner_id.id
                    }) for partner_id in partners_to
                ],
                'channel_type': 'chat',
                'name': ', '.join(self.env['res.partner'].sudo().browse(partners_to).mapped('name')),
            })
            channel._broadcast(partners_to)

        result = self._send_action(message_id, content, author_name, message_date, channel)
        result['channel_id'] =  channel.id


        return result
    
    def action_pin(self):
        CUPC = self.env['current.user.pinned.channel']
        current_user = self.env.user
        cupc_ids = CUPC.search([('user_id', '=', current_user.id), 
                    ('channel_id', '!=', False), ('is_pinned','=',True)])
        
        # Tăng tất cả sequence của channel +1
        for cupc in cupc_ids:
            cupc_ids.write({
                'sequence':  cupc.sequence + 1
            })

        current= cupc_ids.filtered(lambda l: l.channel_id==self)
        if not current:
            CUPC.create({
                'channel_id': self.id,
                'user_id': current_user.id,
                'is_pinned': True,
                'sequence': 1
            })
        else:
            current[0].write({
                'is_pinned': True,
                'sequence': 1
            })
        
        cupcs = CUPC.search([('channel_id', '=', self.id), 
                ('user_id', '=', current_user.id), 
                ('is_pinned','=',True)]).sorted('sequence')

        return [{'parnter_id': cupc.user_id and cupc.user_id.id or False, 
            'channel_id': cupc.channel_id and cupc.channel_id.id or False,
            'sequence': cupc.sequence,
            'is_pinned': cupc.is_pinned
            } for cupc in cupcs]

    def action_unpin(self):
        CUPC = self.env['current.user.pinned.channel']
        current_user = self.env.user
        cupc = CUPC.search([('user_id', '=', current_user.id), ('channel_id', '!=', False), 
                            ('channel_id','=', self.id), ('is_pinned','=',True)], limit=1)

        if cupc:
            cupc.unlink()

        cupcs = CUPC.search([('channel_id', '=', self.id), ('user_id', '=', current_user.id), ('is_pinned','=',True)]).sorted('sequence')

        return [{'parnter_id': cupc.user_id and cupc.user_id.id or False, 
                                                                'channel_id': cupc.channel_id and cupc.channel_id.id or False,
                                                                'sequence': cupc.sequence or 0.0,
                                                                'is_pinned': cupc.is_pinned or False
                                                                } for cupc in cupcs]


    def channel_info(self):
        """ Get the informations header for the current channels
            :returns a list of channels values
            :rtype : list(dict)
        """
        channel_infos = super(MailChannel, self).channel_info()
        current_user = self.env.user
        
                
        CUPC = self.env['current.user.pinned.channel']
        
        for key, dict_info in enumerate(channel_infos, 0):
            for channel in self:
                cupcs = CUPC.search([('channel_id', '=', channel.id), ('user_id', '=', current_user.id), ('is_pinned','=',True)])
                if channel.id==dict_info.get('id', 0):
                    dict_info['member_seen_channel'] = [('insert', [{'id': partner.id, 'name': partner.name} for partner in channel.members_seen_channel])]
                    # dict_info['show_read'] = channel.show_read
                    # dict_info['is_pinned_channel'] = channel.is_pinned_channel
                    dict_info['no_pinned_channel'] = channel.no_pinned_channel
                    partner_seen_channel_ids = channel.mapped('partner_seen_channel_ids')
                    if partner_seen_channel_ids:
                        dict_info['time_partner_seen_channel'] = [{'partner_id': item.partner_id.id if item.partner_id else False,  
                                                        'time_seen': convert_datetime(item.seen_time),
                                                        'localId': item.id
                                                        } for item in partner_seen_channel_ids]
                        five_last_seen, last_count =  channel.get_five_last_seen_and_last_count()
                        dict_info['five_last_seen'] = five_last_seen
                        dict_info['last_count'] = last_count
                    if cupcs:
                        dict_info['current_user_pinned_channel'] = [{'parnter_id': cupc.user_id and cupc.user_id.id or False, 
                                                                'channel_id': cupc.channel_id and cupc.channel_id.id or False,
                                                                'sequence': cupc.sequence,
                                                                'is_pinned': cupc.is_pinned 
                                                                } for cupc in cupcs]
                            
                    break

            channel_infos[key] = dict_info
        
        return channel_infos

    # @api.model
    def last_message_id_by(self):
        self.env.cr.execute("""
            SELECT res_id  as id, max(id) as massage_id
            FROM mail_message 
            WHERE model='mail.channel' and  res_id = %s
            GROUP BY res_id
        """ % (self.id))

        return self.env.cr.dictfetchall()


    def update_members_seen_channel(self, partner_id, is_new_message=False):
        dict_result = {'member_seen_channel': [('insert', [])], 'message_id': 0}
        MailChannel = self.env['mail.channel']
        psc_id = PartnerSeenChannel = self.env['partner.seen.channel']
        channel_id = self.sudo()
        all_channel = MailChannel.search([])

        if channel_id in all_channel:
            last_message_record = channel_id.last_message_id_by()
            if partner_id not in channel_id.partner_seen_channel_ids.mapped('partner_id').ids:
                psc_id = PartnerSeenChannel.create({
                    'partner_id': partner_id, 
                    'seen_time': fields.Datetime.now() + timedelta(hours=7),
                    'channel_id': channel_id.id
                })

            if is_new_message:
                channel_id.write({
                    'last_message_seen_id': int(last_message_record[0].get('massage_id')) + 1 if last_message_record else 0,
                    'members_seen_channel': [(6, 0, [partner_id])],
                    'partner_seen_channel_ids': [(6, 0, list(set(psc_id.ids)))]
                })
                dict_result['message_id'] = int(last_message_record[0].get('massage_id')) + 1 if last_message_record else False

            elif last_message_record and last_message_record[0].get('massage_id') == channel_id.last_message_seen_id:
                print('Case 2: ')
                channel_id.write({
                    'members_seen_channel': [(6, 0, list(set(channel_id.members_seen_channel.ids  + [partner_id])))],
                    'partner_seen_channel_ids': [(6, 0, list(set(channel_id.partner_seen_channel_ids.ids + psc_id.ids)))]
                })
                dict_result['message_id'] = int(last_message_record[0].get('massage_id')) if last_message_record else False

            elif last_message_record and last_message_record[0].get('massage_id') != channel_id.last_message_seen_id:
                print('Case 3: ')
                channel_id.write({
                    'last_message_seen_id': int(last_message_record[0].get('massage_id')),
                    'members_seen_channel': [(6, 0, [partner_id])],
                    'partner_seen_channel_ids': [(6, 0, list(set(psc_id.ids)))]
                })
                
                dict_result['message_id'] = int(last_message_record[0].get('massage_id')) if last_message_record else False

        if channel_id.members_seen_channel:
            dict_result['member_seen_channel'] = [('insert', [{'id': partner.id, 'name': partner.name} for partner in channel_id.members_seen_channel])]
            dict_result['partners']= list(channel_id.members_seen_channel.mail_partner_format().values())
        if channel_id.partner_seen_channel_ids:
            dict_result['time_partner_seen_channel'] = [{'partner_id': item.partner_id.id if item.partner_id else False,  
                                                'time_seen': convert_datetime(item.seen_time),
                                                'localId': item.id,
                                                } for item in channel_id.partner_seen_channel_ids]

            five_last_seen, last_count =  channel_id.get_five_last_seen_and_last_count()
            dict_result['five_last_seen'] = five_last_seen
            dict_result['last_count'] = last_count

        return dict_result
    
    @api.model
    def reload(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def search_messages_exits_channel(self, value):
        messages = self.env['mail.message'].search([('res_id', '=', self.id), ('message_type', '=', 'comment')
                , ('model', '=', 'mail.channel'), ('body', 'ilike', value)])
        
        return True if messages else False
    
    def get_five_last_seen_and_last_count(self):
        """
            output:
                five_last_seen: Get 5 message viewers on all message viewers
                last_count: Remaining viewers of the 5 people who viewed the message
        """
        five_last_seen = []
        last_count = 0
        current_partner = self.env.user.partner_id 
        if self.show_read:
            psc_ids = self.partner_seen_channel_ids.filtered(lambda l: l.partner_id != current_partner).sorted(lambda s: s.seen_time, reverse=True)
            for idx, psc_id in enumerate(psc_ids, 1):
                data = {
                    'partner_id': psc_id.partner_id and psc_id.partner_id.id or False,
                    'time_seen': convert_datetime(psc_id.seen_time),
                    'localId': psc_id.id
                }
                five_last_seen.append(data)
                if idx == 3:
                    break

            last_count = len(psc_ids) - 3
        # else:
             # _logger.info(_("User %s does not have permission to view messages on this channel !!!") % current_partner.name)

        return five_last_seen, last_count 
    # ------------------------END -------------------------#




