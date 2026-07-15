/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one, attr } from '@mail/model/model_field';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';
import { clear } from "@mail/model/model_field_command";


registerPatch({
    name: "ChatWindow",
    recordMethods: {
        closeChatWindowMuteNotifyDialog() {
            this.update({ muteNotifyDialog: clear() });
        },

        selectChatWindowMuteNotifyType(subtype) {
            this.update( {selectedMuteNotifyType: subtype} )
        },

        async updateChatWindowMuteNotifyMailChannel() {
            const kwargs = {
                user_id: this.env.services.user.userId,
                channel_id: this.thread.id,
                mute_notify_type: this.selectedMuteNotifyType === false ? "1_hour" : this.selectedMuteNotifyType
            };
            await this.messaging.rpc({
                model: "notify.mail.channel",
                method: "action_mute_notify_mail_channel",
                args: [[false]],
                kwargs,
            });
            this.thread.update( {isMuteNotify: true, muteNotifyType: kwargs.mute_notify_type} );
            this.closeChatWindowMuteNotifyDialog();
        },

        async turnOffChatWindowMuteNotifyMailChannel(ev){
            markEventHandled(ev, "ChatWindow.onClickCommand");
            const kwargs = {
                user_id: this.env.services.user.userId,
                channel_id: this.thread.id,
                mute_notify_type: false
            };
            await this.messaging.rpc({
                model: "notify.mail.channel",
                method: "action_mute_notify_mail_channel",
                args: [[false]],
                kwargs,
            });
            this.thread.update( {isMuteNotify: false, muteNotifyType: false} );
        },

        onClickShowMuteNotifyDialog(ev) {
            markEventHandled(ev, "ChatWindow.onClickCommand");
            this.update({
                muteNotifyDialog: {}
            });
        }
    },
    fields: {
        isMuteNotify: attr({
            compute() {
                if(this.thread && this.thread.isMuteNotify) {
                    return this.thread.isMuteNotify;
                }
                return clear();
            }
        }),
        selectedMuteNotifyType: attr({
            compute() {
                if (this.thread && this.thread.isMuteNotify){
                    return this.thread.muteNotifyType;
                }
                return clear();
            },
            default: false
        }),
        muteNotifyDialog: one("Dialog", {
            inverse: "chatWindowMuteNotifyDialog",
        }),
    }
})
