/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { clear, link, insert } from '@mail/model/model_field_command';


registerPatch({
    name: 'Channel',
    recordMethods: {
        async searchMessageExistsInChannel(value){
            const checked = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'search_messages_exits_channel',
                kwargs: { value: value},
                args: [[this.id]],
            });
            
            this.update({
                hasBeenFound: checked
            })
        },

        async onClickPinChannel(ev) {
            const cupc_data = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'action_pin',
                args: [[this.id]],
            });

            if(cupc_data && this.thread){
                this.thread.update({ currentUserPinnedChannel: cupc_data});
            }else{
                console.log('Valid onClickPinChannel !!!')
            }

            let threads = this.messaging.allCurrentClientThreads
            for(const i in threads){
                threads[i].update({
                    noPinnedChannel: threads[i].noPinnedChannel + 1
                })
            }
        },
        
        async onClickUnPinChannel(ev) {
            const cupc_data = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'action_unpin',
                args: [[this.id]],
            });
            
            if(cupc_data && this.thread){
                this.thread.update({ currentUserPinnedChannel: cupc_data});
            }else{
                console.log('Valid onClickUnPinChannel !!!')
            }
        },
    },
    fields: {
        
        messageViewCategory: one('MessageView', {
            compute() {
                switch (this.channel_type) {
                    case 'channel':
                        return this.messaging.discuss.categoryChannel;
                    case 'chat':
                    case 'group':
                        return this.messaging.discuss.categoryChat;
                    default:
                        return clear();
                }
            },
        }),

        messageForwardCategoryItem: one('MessageForwardCategoryItem', {
            compute() {
                if (!this.thread) {
                    return clear();
                }
                if (!this.thread.isPinned) {
                    return clear();
                }
                if (!this.messageViewCategory) {
                    return clear();
                }
                return { category: this.messageViewCategory };
            },
            inverse: 'channel',
        }),

        hasBeenFound: attr({
            default: false,
        }),
        
        currentUserPinnedChannel: attr({
            related: 'thread.currentUserPinnedChannel'
        }),

        isPinnedChannel: attr({
            related: 'thread.isPinnedChannel'
        }),

        noPinnedChannel: attr({
            related: 'thread.noPinnedChannel'
        }),

        partnerSeenChannel: many('Partner'),

    },
});
