/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';


registerPatch({
    name: "ThreadViewTopbar",
    recordMethods: {
        onClickShowMuteNotifyDialog() {
            this.thread.update({
                muteNotifyDialog: {} //If you has record in models you can push value to this fields
            });
        },
        onClickTurnOffMuteNotify() {
            this.thread.turnOffMuteNotifyMailChannel();
        },
    },
});
