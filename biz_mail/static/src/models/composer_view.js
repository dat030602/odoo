/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'ComposerView',
    recordMethods: {
        async postMessage() {
            this._super()
            if(this.composer && this.composer.thread){
                this.composer.thread.updateMembersSeenChannel()
            }else{
                console.log('Channel not found !!!!')
            }
        },
    },
});
