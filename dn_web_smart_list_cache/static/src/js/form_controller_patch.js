/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { onWillUnmount } from "@odoo/owl";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);

        // When main form unmounts (e.g. navigating back to list), set return flag and source model
        onWillUnmount(() => {
            // Ignore modal/dialog forms (wizards, popups, quick create)
            if (this.env?.inDialog) {
                return;
            }

            const cacheService = this.env?.services?.smart_list_cache;
            // Only set return flag if this form matches the expected return model
            if (cacheService && cacheService.expectedReturnModel === this.props.resModel) {
                cacheService.isReturningFromForm = true;
                cacheService.sourceModel = this.props.resModel;
                cacheService.sourceActionId = this.env?.config?.actionId;
            }
        });
    },

    /**
     * Intercept standard form save (button click, shortcut, or auto-save on leave).
     */
    async save(params) {
        const isNew = this.model?.root?.isNew;
        const saved = await super.save(...arguments);
        const cacheService = this.env?.services?.smart_list_cache;

        if (saved && cacheService && this.model?.root?.resId) {
            const resModel = this.model.root.resModel;
            const resId = this.model.root.resId;

            // Separate new record creation from regular modification
            if (isNew) {
                cacheService.markCreated(resModel, resId);
            } else {
                cacheService.markDirty(resModel, resId);
            }
        }
        return saved;
    },

    /**
     * Intercept deletion dialog confirmation callback to track deleted record ID
     * before back navigation starts.
     */
    get deleteConfirmationDialogProps() {
        const dialogProps = super.deleteConfirmationDialogProps;
        const originalConfirm = dialogProps.confirm;
        const record = this.model?.root;
        const resModel = record?.resModel;
        const resId = record?.resId;

        dialogProps.confirm = async () => {
            // Register deletion BEFORE back navigation (historyBack) occurs inside originalConfirm
            const cacheService = this.env?.services?.smart_list_cache;
            if (cacheService && resModel && resId) {
                cacheService.markDeleted(resModel, resId);
            }
            await originalConfirm();
        };
        return dialogProps;
    },

    /**
     * Intercept direct deleteRecord call if applicable.
     */
    async deleteRecord() {
        const record = this.model?.root;
        const resModel = record?.resModel;
        const resId = record?.resId;

        const isDeleted = await super.deleteRecord?.(...arguments);
        const cacheService = this.env?.services?.smart_list_cache;
        if (isDeleted && cacheService && resModel && resId) {
            cacheService.markDeleted(resModel, resId);
        }
        return isDeleted;
    },
});
