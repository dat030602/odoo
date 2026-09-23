/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { onWillUnmount } from "@odoo/owl";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        
        const silentReload = async () => {
            if (this.model && this.model.root) {
                await this.model.root.load();
                this.model.notify();
            }
        };

        this.env.bus.addEventListener("dn_notification_fetch_record_fetch_record", silentReload);

        onWillUnmount(() => {
            this.env.bus.removeEventListener("dn_notification_fetch_record_fetch_record", silentReload);
        });
    }
});

