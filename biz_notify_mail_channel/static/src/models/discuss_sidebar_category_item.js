/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'DiscussSidebarCategoryItem',
    fields: {
        // Inherit
        counter: {
            compute() {
                if (!this.thread) {
                    return clear();
                }
                switch (this.channel.channel_type) {
                    case 'channel':
                        return this.channel.localMessageUnreadCounter;
                }
                return this._super(...arguments);
            },
        },
    },
});
