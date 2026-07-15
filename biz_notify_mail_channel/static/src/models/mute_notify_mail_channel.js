/** @odoo-module **/

import { registerModel } from "@mail/model/model_core";
import { attr, many, one } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";

registerModel({
    name: "MuteNotifyMailChannel",
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
            $(".o_MuteNotifyMailChannel_item").find('input[type="radio"]').prop("checked", false);
            $(ev.target).prop("checked", true);
            this.muteNotifyDialog.selectMuteNotifyType(item.key);
        },
        onClickApply(ev) {
            this.muteNotifyDialog.updateMuteNotifyMailChannel();
        },
        onClickCancel(ev) {
            this.muteNotifyDialog.closeMuteNotifyDialog();
        },
    },
    fields: {
        component: attr(),

        dialogMailChannel: one("Dialog", {
            identifying: true,
            inverse: "muteNotifyMailChannel",
            isCausal: true,
        }),
        muteNotifyDialog: one("Thread", {
            related: "dialogMailChannel.muteNotifyDialog",
            required: true,
        }),

    }
});
