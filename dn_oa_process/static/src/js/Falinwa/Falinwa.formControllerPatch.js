/** @odoo-module */
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { session } from "@web/session";

function getEngine() {
    return (typeof odoo !== "undefined" && odoo._mb && odoo._mb.ValidationProcess) || false;
}

function isVprocessModel(model) {
    const models = session.vprocess_models || [];
    return !!model && models.includes(model);
}

function refreshCurrentRecord(controller) {
    const inst = getEngine();
    const root = controller.model && controller.model.root;
    const model = controller.props.resModel;
    const resId = root && root.resId;
    if (inst && isVprocessModel(model)) {
        inst.refresh(model, resId).catch(() => {});
    }
}

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        const self = this;

        onMounted(() => {
            refreshCurrentRecord(self);
        });

        onPatched(() => {
            refreshCurrentRecord(self);
        });

        onWillUnmount(() => {
            const inst = getEngine();
            const model = self.props.resModel;
            if (inst && isVprocessModel(model)) {
                inst.removeContainer();
                inst.clearLocks();
                inst.refreshKey = null;
            }
        });
    },

    async onRecordSaved(record, changes) {
        const res = await super.onRecordSaved(...arguments);
        refreshCurrentRecord(this);
        return res;
    },
});
