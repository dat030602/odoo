/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { cleanSearchTerm } from '@mail/utils/utils';
var core = require('web.core');
var _t = core._t;
import { auto_str_to_date, getLangDateFormat, getLangDatetimeFormat } from 'web.time';

registerPatch({
    name: 'MessageView',
    recordMethods: {

        _onKeydownTextarea: function (ev) {
            
            switch (ev.key) {
                case 'Enter':
                    this.update({ 
                        searchTerm: ev.target.value,
                        // sendMessageContent: $(".o_TypeMessage").val(),
                        // hasSearchChannels: true
                    });
                    this.searchPartnersToForward();
                    this.update({
                        showForwardDialog: false
                    });
            }
        },

        onClickChannelTab(ev) {
            
            var channel_id = "#biz_mail_channel_tab"
            var user_id = "#biz_mail_users_tab"
            var channel_content = "#biz_mail_channels"
            var user_content = "#biz_mail_users"
            $(channel_id).removeClass('active').addClass('active');
            $(channel_content).removeClass('show active').addClass('show active');
            $(user_id).removeClass('active')
            $(user_content).removeClass('show active')
            this.update({
                is_channel_tab: true
            });
        },

        onClickUsersTab(ev) {
            console.log('on click users tab')
            var channel_tab = "#biz_mail_channel_tab"
            var user_tab = "#biz_mail_users_tab"
            var channel_content = "#biz_mail_channels"
            var user_content = "#biz_mail_users"
            $(user_tab).removeClass('active').addClass('active');
            $(user_content).removeClass('show active').addClass('show active');
            $(channel_tab).removeClass('active')
            $(channel_content).removeClass('show active')
            this.update({
                is_channel_tab: false
            });
        },

        async onClickSendForwardToChannel(channel, ev){
            ev.stopPropagation();
            var forwardChannelId  = "#forwardChannelId_" + channel.id
            var typedMessage = $(".o_TypeMessage").val()
            

            if (_t('Send') == $(forwardChannelId).text()){
                try {
                    const channelId = (channel && channel.model === 'mail.channel') ? channel.id : undefined;
                    // message_id: message_id, body: content, channel_id: channel_id
                    const { success: isSuccess, message_id: messageID, body: content, attachment_ids: attachmentIDs } = await this.messaging.rpc(
                        {
                            model: 'mail.channel',
                            method: 'send_message_to_channel',
                            kwargs: {
                                message_id: this.message.id,
                                content: typedMessage,
                                author_name: this.message.author.nameOrDisplayName,
                                message_date: this.message.date.format(getLangDatetimeFormat()),
                                to_channel: channelId,
                            },
                        },
                        { shadow: true }
                    );
                    if (isSuccess){
                        
                        const postData = {
                            is_forward: true,
                            attachment_ids: attachmentIDs,
                            body: content,
                            message_type: 'comment',
                            partner_ids: [],
                        };
                    
                        const params = {
                            'post_data': postData,
                            'thread_id': channel.id,
                            'thread_model': 'mail.channel',
                        };
                        
                        // const messageData = await this.env.services.rpc({ route: `/mail/message/post`, params });
                        params.context = {mail_post_autofollow: true}
                        const messageData = await this.messaging.rpc({ route: `/mail/message/post`, params });
                        $(forwardChannelId).text(_t('Sent'));
                        $(forwardChannelId).removeClass('biz-btn-primary').addClass('biz-btn-secondary');
                    }
                    return
                   
                } finally {
        
                }
            }
        },

        /**
        * Handles click on the "Forward To Parnter" button.
        ** @param {mail.partner} partner
        * @param {MouseEvent} ev
        */
        async onClickSendForwardToUser(partner, ev){
            ev.stopPropagation();
            var forwardID = "#forward_id_" + partner
            var typedMessage = $(".o_TypeMessage").val()
            const channelId = (this.messaging.discuss.thread.channel) ? this.messaging.discuss.thread.channel.id : undefined;
            
            if (_t('Send') == $(forwardID).text()){
                try {
                    const { success: isSuccess, message_id: messageID, 
                            body: content, channel_id: channelID, 
                            attachment_ids: attachmentIds
                        } = await this.messaging.rpc(
                        {
                            model: 'mail.channel',
                            method: 'send_message_to_user',
                            kwargs: {
                                to_partner: partner,
                                content: typedMessage,
                                message_id: this.message.id,
                                author_name: this.message.author.nameOrDisplayName,
                                message_date: this.message.date.format(getLangDatetimeFormat()),
                                
                            },
                        },
                        { shadow: true }
                    );
                    if (isSuccess){
                        const postData = {
                            is_forward: true,
                            attachment_ids: attachmentIds,
                            body: content,
                            message_type: 'comment',
                            partner_ids: [],
                        };
                    
                        const params = {
                            'post_data': postData,
                            'thread_id': channelID,
                            'thread_model': 'mail.channel',
                        };
                        const messageData = await this.messaging.rpc({ route: `/mail/message/post`, params });
                        
                        $(forwardID).text(_t('Sent'));
                        $(forwardID).disabled = true;
                        $(forwardID).removeClass('biz-btn-primary').addClass('biz-btn-secondary');
                    }
                        
                }finally{
        
                }
            }
        
        },

        async searchPartnersToForward() {
            if (this.hasSearchRpcInProgress) {
                this.update({ hasPendingSearchRpc: true });
                return;
            }
            this.update({
                hasPendingSearchRpc: false,
                hasSearchRpcInProgress: true,
            });
            try {
                const channelId = (this.message && this.message.originThread && this.message.originThread.model === 'mail.channel') ? this.message.originThread.id : undefined;
                
                const { partners: partnersData } = await this.messaging.rpc(
                    {
                        model: 'res.partner',
                        method: 'search_for_user_forward',
                        kwargs: {
                            channel_id: channelId,
                            search_term: cleanSearchTerm(this.searchTerm),
                        },
                    },
                    { shadow: true }
                );
                if (!this.exists()) {
                    return;
                }
                this.update({
                    selectablePartners: partnersData,
                });
            } finally {
                if (this.exists()) {
                    this.update({ hasSearchRpcInProgress: false });
                    if (this.hasPendingSearchRpc) {
                        this.searchPartnersToForward();
                    }
                }
            }
        },

        /**
         * @param {MouseEvent} ev
         */
        async onClickLoadSeenMessage(ev) {
            if(this.messaging && this.messaging.discuss && this.messaging.discuss.thread){
                this.messaging.discuss.thread.updateMembersSeenChannel()
            }else{
                console.log('Channel not found !!!!')
            }
        },


    },
    fields: {
        forwardMessageConfirmViewOwner: one('ForwardMessageConfirmView', {
            identifying: true,
            inverse: 'messageView',
        }),
        
        message: {
            compute() {
                if (this.forwardMessageConfirmViewOwner) {
                    return this.forwardMessageConfirmViewOwner.message;
                }
                return this._super()
            }
        },

        is_channel_tab: attr({
            default: true,
        }),

        categoryItems: many('MessageForwardCategoryItem', {
            compute() {
                let channels = this.messaging.allCurrentClientThreads
                const searchValue = this.searchTerm;
                if (searchValue){
                    const qsVal = searchValue.toLowerCase();
                    channels = channels.filter(t => {
                        const nameVal = t.displayName.toLowerCase();
                        return nameVal.includes(qsVal);
                    });
                }

                return channels.map(channel => {
                    return { channel };
                });
            },
            inverse: 'category',
        }),

        selectablePartners: many('Partner'),
    
        searchTerm: attr({
            default: "",
        }),
        hasSearchRpcInProgress: attr({
            default: false,
        }),

        hasPendingSearchRpc: attr({
            default: false,
        }),


        // overide
        // remove condition
        // case 1: hasSeenIndicators: direct messages
        // case 2: ! hasSeenIndicators: channel
        messageSeenIndicatorView: {
            compute() {
                if (
                    // this.message.isCurrentUserOrGuestAuthor &&
                    this.messageListViewItemOwner &&
                    this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread
                ) {
                    return {};
                }
                return clear();
            },
        },
        // output:
        // true: DirectMessages
        // false: Channel
        isDirectMessages: attr({
            compute() {
                if (this.messageListViewItemOwner && 
                    this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread && 
                    this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread.hasSeenIndicators
                    ){
                        return true
                }
                return false
            },
            default: false,
        }),
        
    },
});
