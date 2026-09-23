/** @odoo-module **/

import { registry } from "@web/core/registry";

export const customApprovalService = {
    dependencies: ["notification"],
    start(env, { notification }) {
        const originalAdd = notification.add.bind(notification);
        notification.add = (message, options = {}) => {
            if (options.type && options.type.toString() !== 'danger') {
                env.bus.trigger("dn_notification_fetch_record_fetch_record");
            }
            return originalAdd(message, options);
        };
        return {};
    },
};

registry.category("services").add("dn_notification_fetch_record.custom_logic", customApprovalService);

