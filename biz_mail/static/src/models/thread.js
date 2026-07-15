/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { clear, link, insert } from '@mail/model/model_field_command';

registerPatch({
    name: 'Thread',
    recordMethods: {
        async updateMembersSeenChannel(ev) {
            var currentPartner = this.messaging.currentPartner.id
            
            if (typeof this.id === 'number' || this.id instanceof Number){
                const { member_seen_channel: memberSeenChannel,
                        message_id: messageID, 
                        partners: partnersData,
                        time_partner_seen_channel: timePartnerSeenChannel,
                        five_last_seen: fiveLastSeen,
                        last_count: lastCount
                    } = await this.messaging.rpc({
                    model: 'mail.channel',
                    method: 'update_members_seen_channel',
                    args: [[this.id]],
                    kwargs: {
                        partner_id: currentPartner
                    },
                    
                }, { shadow: true });

                if (partnersData){
                    for (const i in partnersData){
                        const partner = this.messaging.models['Partner'].insert({
                            id: partnersData[i].id,
                            name: partnersData[i].name,
                        });
                        
                        this.update({ partnerSeenChannel: link(partner),
                            timePartnerSeenChannel: timePartnerSeenChannel,
                            fiveLastSeen: fiveLastSeen,
                            lastCount: lastCount
                        });
                    }
                }
            }else{
                console.log('This action is not support !!!')
            }
        }
    },
    modelMethods: {
        convertData(data) {
            const data2 = this._super(data);
            if ('member_seen_channel' in data){
                data2.partnerSeenChannel = data.member_seen_channel;
            }
            
            // if ('show_read' in data){
            //     data2.showRead = data.show_read;
            // }
            if('is_pinned_channel' in data){
                data2.isPinnedChannel = data.is_pinned_channel
            }
            // if('messagesOfThread' in data){
            //     data2.messagesOfThread = data.messagesOfThread
            // }
            if('no_pinned_channel' in data){
                data2.noPinnedChannel = data.no_pinned_channel
            }
            if ('time_partner_seen_channel' in data){
                data2.timePartnerSeenChannel = data.time_partner_seen_channel
                // data2.timePartnerSeenChannelReverse = data.time_partner_seen_channel.reverse()
            }
            if ('current_user_pinned_channel' in data){
                data2.currentUserPinnedChannel = data.current_user_pinned_channel
            }
            if ('five_last_seen' in data){
                data2.fiveLastSeen = data.five_last_seen
            }
            if ('last_count' in data){
                data2.lastCount = data.last_count
            }
            
            
            return data2;
        },

        async createGroupChat({ default_display_mode, partners_to }) {
            console.log('Overide........Tao nhom chat....123123')
            debugger
            const channelData = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'create_group',
                kwargs: {
                    default_display_mode,
                    partners_to,
                    context: { active_test: false },
                },
            });
            return this.messaging.models['Thread'].insert(
                this.messaging.models['Thread'].convertData(channelData)
            );
        },
    },
    fields: {
        currentUserPinnedChannel: attr({
            default: []
        }),

        isPinnedChannel: attr({
            // compute: '_computeIsPinnedChannel',
            // default: false,
            // default: false,
            compute() {
                var isPinnned = false
                if(this.currentUserPinnedChannel && this.currentUserPinnedChannel.length >= 1){
                    isPinnned = true
                }
                return isPinnned
            },
            default: false,
        }),

        // Tinh Lai
        noPinnedChannel: attr({
            compute() {
                var sequence = 0
                if(this.currentUserPinnedChannel && this.currentUserPinnedChannel.length >= 1){
                    sequence = this.currentUserPinnedChannel[0]['sequence']
                }
                return sequence
            },
            default: 0,
        }),

        partnerSeenChannel: many('Partner'),
        // has partner && time seen
        timePartnerSeenChannel: attr({
            default: []
        }),

        fiveLastSeen: attr({
            default: []
        }),

        lastCount: attr({
            default: 0
        }),
    },
});
