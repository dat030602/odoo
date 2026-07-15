/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from "@mail/model/model_field_command";


registerPatch({
    name: "Dialog",
    fields: {
        muteNotifyDialog: one("Thread", {
            identifying: true,
            inverse: "muteNotifyDialog",
        }),
        muteNotifyMailChannel: one("MuteNotifyMailChannel", {
            compute() {
                return this.muteNotifyDialog ? {} : clear();
            },
            inverse: 'dialogMailChannel',
        }),

        chatWindowMuteNotifyDialog: one("ChatWindow", {
            identifying: true,
            inverse: "muteNotifyDialog",
        }),
        chatWindowMuteNotifyMailChannel: one("ChatWindowMuteNotifyMailChannel", {
            compute() {
                return this.chatWindowMuteNotifyDialog ? {} : clear();
            },
            inverse: 'chatWindowDialogMailChannel',
        }),

        // Inherit
        componentName: {
            compute() {
                if (this.muteNotifyMailChannel) {
                    return "MuteNotifyMailChannel";
                }
                if (this.chatWindowMuteNotifyMailChannel) {
                    return "ChatWindowMuteNotifyMailChannel";
                }
                return this._super(...arguments);
            },
        },
        record: {
            compute() {
                if (this.muteNotifyMailChannel) {
                    return this.muteNotifyMailChannel;
                }
                if (this.chatWindowMuteNotifyMailChannel) {
                    return this.chatWindowMuteNotifyMailChannel;
                }
                return this._super(...arguments);
            },
        }
    }
})