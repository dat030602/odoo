/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'Discuss',
    recordMethods: {
        onInputGroupMessagesSearch(value) {
            // step 1: search group
            if (!this.sidebarGroupsMessagesValue) {
                this.categoryChat.open();
                this.categoryChannel.open();
            }
            let channels = this.messaging.allCurrentClientThreads.map(x=>x.channel)

            for(const i in channels){
                channels[i].searchMessageExistsInChannel(value)
            }

            this.update({ sidebarGroupsMessagesValue: value });
            // step 2: search message by group
            if (this.threadView && this.threadView.messageListView){
                this.threadView.messageListView.onInputMessageSearch(value)
            }
        },
    },
    fields: {
        sidebarGroupsMessagesValue: attr({
            default: "",
        }),

        
    },
});
