/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'DiscussView',
    recordMethods: {
        onInputGroupMessagesSearch(ev) {
            ev.stopPropagation();
            this.discuss.onInputGroupMessagesSearch(this.groupMessagesSearchInput.el.value);
        },
    },
    fields: {
        // secondCategoryChannel: one('MessageView', {
        //     default: {},
        //     inverse: 'discussAsChannel',
        // }),

        groupMessagesSearchInput: attr(),
    },
});
