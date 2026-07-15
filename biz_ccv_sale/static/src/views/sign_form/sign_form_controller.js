/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { useSignViewButtons } from "@sign/views/hooks";

export class SignFormController extends FormController {
    setup() {
        super.setup(...arguments);
        const functions = useSignViewButtons();
        Object.assign(this, functions);
    }
}
