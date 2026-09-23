import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useState, onMounted, onWillUnmount } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        
        const isFullWidth = browser.localStorage.getItem("dn_form_full_width") === "true";
        this.dnFullWidthState = useState({
            isActive: isFullWidth,
        });

        onMounted(() => {
            this.applyDnFullWidthClass(this.dnFullWidthState.isActive);
        });

        onWillUnmount(() => {
            document.body.classList.remove("dn_form_full_width");
        });
    },

    toggleDnFullWidth() {
        this.dnFullWidthState.isActive = !this.dnFullWidthState.isActive;
        this.applyDnFullWidthClass(this.dnFullWidthState.isActive);
        
        // Save to browser cache
        browser.localStorage.setItem("dn_form_full_width", this.dnFullWidthState.isActive);
    },

    applyDnFullWidthClass(isActive) {
        if (isActive) {
            document.body.classList.add("dn_form_full_width");
        } else {
            document.body.classList.remove("dn_form_full_width");
        }
    }
});
