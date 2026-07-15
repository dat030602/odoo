odoo.define('biz_ods.PhoneCallTab', function (require) {
    "use strict";

    const PhoneCallTab = require('voip.PhoneCallTab');

    PhoneCallTab.include({
        /**
         * Triggers the hangup process then refreshes the tab.
         *
         * @param {boolean} isDone
         * @return {Promise}
         */
        async hangupPhonecall(isDone) {
            this._super.apply(this, arguments);
            setTimeout(location.reload(), 900);
        },
        /**
         * called when canceling an outgoing call
         *
         * @return {Promise}
         */
        async onCancelOutgoingCall() {
            if (!this._currentPhoneCallId) {
                return;
            }
            this._super.apply(this, arguments);
            setTimeout(location.reload(), 900);
        },
    })
});