/** @odoo-module */

import { FormController } from '@web/views/form/form_controller';
import { patch } from "@web/core/utils/patch";

const FormControllerDeleteRouter = {
	get deleteConfirmationDialogProps() {
		if (this.model.root.resModel ==  'sale.route'){
			return {
	            body: this.env._t("Deleting the route will delete all contact lines attached to the route, delete the check-in/check-out in the route?"),
	            confirm: async () => {
	                await this.model.root.delete();
	                if (!this.model.root.resId) {
	                    this.env.config.historyBack();
	                }
	            },
	            cancel: () => {},
	        };
		}else{
	        return this._super.apply(this, arguments);
		}
    }
}
patch(FormController.prototype, 'form_controller_ondelete_record_router', FormControllerDeleteRouter);
