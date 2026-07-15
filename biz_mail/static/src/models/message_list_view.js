/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'MessageListView',
    recordMethods: {
        onInputMessageSearch(value) {
            this.update({
                messageSearchInput: value
            })
            // ev.stopPropagation();
            // this.messageListView.onInputMessageSearch(this.messageSearchInput.el.value);
        },
    },
    fields: {
        messageSearchInput: attr(),
    },
});
