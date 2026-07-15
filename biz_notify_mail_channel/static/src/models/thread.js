/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from "@mail/model/model_field_command";

registerPatch({
    name: "Thread",
    modelMethods: {
        convertData(data) {
            var data2 = this._super(data);
            if("is_mute_notify" in data){
                data2.isMuteNotify = data.is_mute_notify;
            }
            if("mute_notify_type" in data){
                data2.muteNotifyType = data.mute_notify_type;
            }
            return data2;
        }
    },
    recordMethods: {
        closeMuteNotifyDialog() {
            this.update({ muteNotifyDialog: clear() });
        },

        selectMuteNotifyType(subtype) {
            this.update( {muteNotifyType: subtype} )
        },

        async updateMuteNotifyMailChannel() {
            const kwargs = {
                user_id: this.env.services.user.userId,
                channel_id: this.id,
                mute_notify_type: this.muteNotifyType === false ? "1_hour" : this.muteNotifyType
            };
            await this.messaging.rpc({
                model: "notify.mail.channel",
                method: "action_mute_notify_mail_channel",
                args: [[false]],
                kwargs,
            });
            this.update( {isMuteNotify: true, muteNotifyType: kwargs.mute_notify_type} );
            this.closeMuteNotifyDialog();
        },

        async turnOffMuteNotifyMailChannel(){
            const kwargs = {
                user_id: this.env.services.user.userId,
                channel_id: this.id,
                mute_notify_type: false
            };
            await this.messaging.rpc({
                model: "notify.mail.channel",
                method: "action_mute_notify_mail_channel",
                args: [[false]],
                kwargs,
            });
            this.update( {isMuteNotify: false, muteNotifyType: false} );
        }
    },
    fields: {
        isShowMuteNotifyIcon: attr({
            compute() {
                return this.model === 'mail.channel';
            },
        }),
        isMuteNotify: attr({
            default: false
        }),
        muteNotifyType: attr({
            default: false
        }),

        muteNotifyDialog: one("Dialog", {
            inverse: "muteNotifyDialog",
        }),

        //Inherit
        messagingMenuAsPinnedAndUnreadChannel: {
            compute() {
                if(this.isMuteNotify){
                    if (!this.messaging || !this.messaging.messagingMenu) {
                        return clear();
                    }
                    if (this.channel && this.isPinned && this.channel.localMessageUnreadCounter > 0 && !this.isMuteNotify) {
                        return this.messaging.messagingMenu;
                    }
                    return clear();
                }
                return this._super(...arguments);
            },
        },
    },
});