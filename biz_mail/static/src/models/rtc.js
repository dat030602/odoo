/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';


registerPatch({
    name: 'Rtc',
    fields: {
        /**
            Override
         */
        pingInterval: {
            compute() {
                return this.messaging.browser.setInterval(this._onPingInterval, 60000); // 60 seconds
            },
        },
    },
})