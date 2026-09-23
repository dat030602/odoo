import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(FormController.prototype, {
    get className() {
        const result = super.className;
        
        // Ensure result is an object to modify it
        if (result && typeof result === 'object') {
            const rules = session.dn_hide_chatter_rules || {};
            const resModel = this.props.resModel;
            
            if (rules[resModel]) {
                if (rules[resModel].hide_activity) {
                    result["dn_no_activity"] = true;
                }
                if (rules[resModel].hide_chatter) {
                    result["dn_no_chatter"] = true;
                }
            }
        }
        
        return result;
    }
});
