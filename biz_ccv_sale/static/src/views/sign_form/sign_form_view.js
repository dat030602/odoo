/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { SignFormController } from "@biz_ccv_sale/views/sign_form/sign_form_controller";

export const signFormView = {
    ...formView,
    Controller: SignFormController,
    buttonTemplate: "biz_ccv_sale.SignFormController",
};
registry.category("views").add("sign_form", signFormView);
