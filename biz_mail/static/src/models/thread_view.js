/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'ThreadView',
    recordMethods: {
        onInputMessageSearch(ev) {
            ev.stopPropagation();
            this.messageListView.onInputMessageSearch(this.messageSearchInput.el.value);
        },
        // overide
        handleVisibleMessage(message) {
            if (!this.lastVisibleMessage || this.lastVisibleMessage.id < message.id) {
                this.update({ lastVisibleMessage: message });
                
                if(this.thread && this.thread.isChatChannel){
                    this.thread.updateMembersSeenChannel()
                }else{
                    console.log('Channel not found !!!!')
                }
            }
        },
    
    },
    fields: {
        messageSearchInput: attr(),
    },
});
