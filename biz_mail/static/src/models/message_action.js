/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerPatch({
    name: 'MessageAction',
    fields: {
        messageActionListOwner: {
            compute() {
                if (this.messageActionListOwnerAsForward) {
                    return this.messageActionListOwnerAsForward;
                }
                return this._super()
            },
        },

        messageActionListOwnerAsForward: one('MessageActionList', {
            identifying: true,
            inverse: 'actionForward',
        }),

        sequence: {
            compute() {
                switch (this.messageActionListOwner) {
                    case this.messageActionListOwnerAsForward:
                        return 7;
                }
                return this._super()
            }
        }
        
    },
});
