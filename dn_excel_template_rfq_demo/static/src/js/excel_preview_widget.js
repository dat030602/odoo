/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class ExcelPreviewWidget extends Component {
    static template = "dn_excel_template_rfq_demo.ExcelPreviewWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.actionService = useService("action");
    }

    async onOpenPopup() {
        const recordId = this.props.record.resId;
        if (!recordId) {
            return;
        }
        await this.actionService.doAction("dn_excel_template_rfq_demo.action_excel_template_preview_wizard", {
            additionalContext: {
                default_order_id: recordId,
            },
        });
    }
}

export const excelPreviewWidget = {
    component: ExcelPreviewWidget,
    displayName: "Excel Preview Popup Button",
    supportedTypes: ["char", "boolean", "integer"],
};

registry.category("fields").add("excel_preview_popup", excelPreviewWidget);
