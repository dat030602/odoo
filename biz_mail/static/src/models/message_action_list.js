/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'MessageActionList',
    fields: {
        actionForward: one('MessageAction', {
            compute() {
                if (this.message ) {
                    return {};
                }
                return clear();
            },
            inverse: 'messageActionListOwnerAsForward',
        }),
    },
});
