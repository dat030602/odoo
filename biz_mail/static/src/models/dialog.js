/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'Dialog',
    fields: {
        forwardMessageConfirmView: one('ForwardMessageConfirmView', {
            compute() {
                return this.messageActionViewOwnerAsForwardConfirm ? {} : clear();
            },
            inverse: 'dialogOwner',
        }),

        componentName: {
            compute() {
                if (this.forwardMessageConfirmView) {
                    return 'ForwardMessageConfirm';
                }
                return this._super()
            }
        },

        componentClassName: {
            compute() {
                if (this.forwardMessageConfirmView) {
                    return 'o_Dialog_componentLargeSize align-self-start mt-5';
                }
                return this._super()
            }
        },

        messageActionViewOwnerAsForwardConfirm: one('MessageActionView', {
            identifying: true,
            inverse: 'forwardConfirmDialog',
        }),

        record: {
            compute() {
                if (this.forwardMessageConfirmView) {
                    return this.forwardMessageConfirmView;
                }
                return this._super()
            }
        },
    },
});
