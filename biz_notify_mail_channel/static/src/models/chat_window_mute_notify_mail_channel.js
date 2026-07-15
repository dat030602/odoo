/** @odoo-module **/

import { registerModel } from "@mail/model/model_core";
import { attr, many, one } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";

registerModel({
    name: "ChatWindowMuteNotifyMailChannel",
    recordMethods: {
        /**
         * Returns whether the given html element is inside this follower subtype list.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        containsElement(element) {
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
        },
        onChangeRadio(item, ev) {
            $(".o_ChatWindowMuteNotifyMailChannel_item").find('input[type="radio"]').prop("checked", false);
            $(ev.target).prop("checked", true);
            this.chatWindowMuteNotifyDialog.selectChatWindowMuteNotifyType(item.key);
        },
        onClickApply(ev) {
            this.chatWindowMuteNotifyDialog.updateChatWindowMuteNotifyMailChannel();
        },
        onClickCancel(ev) {
            this.chatWindowMuteNotifyDialog.closeChatWindowMuteNotifyDialog();
        },
    },
    fields: {
        component: attr(),

        chatWindowDialogMailChannel: one("Dialog", {
            identifying: true,
            inverse: "chatWindowMuteNotifyMailChannel",
            isCausal: true,
        }),

        chatWindowMuteNotifyDialog: one("ChatWindow", {
            related: "chatWindowDialogMailChannel.chatWindowMuteNotifyDialog",
            required: true,
        }),
    }
});
