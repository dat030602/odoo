/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'DiscussSidebarCategoryItem',
    recordMethods: {
        onClickPinChannel(ev) {
            ev.stopPropagation();
            this.channel.onClickPinChannel()
        },

        onClickUnPinChannel(ev) {
            ev.stopPropagation();
            this.channel.onClickUnPinChannel()
        },

        onClick(ev) {
            if (this.thread){
                this.thread.updateMembersSeenChannel()
            }else{
                console.log('Channel not found !!!!')
            }
            this._super()
        },        
    },
    fields: {
        is_forward: attr({
            compute() {
                if (this.localId.startsWith('MessageForwardCategoryItem')) {
                    return false;
                }
                return true;
            },
            default: true,
        }),
        
    },
});
