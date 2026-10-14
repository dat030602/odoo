/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onWillStart, onWillUnmount } from "@odoo/owl";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        const cacheService = this.env?.services?.smart_list_cache;

        // Lifecycle hook for list controller unmount
        onWillUnmount(() => {
            // Maintained for clean lifecycle management without corrupting server data with datapoints
        });

        // Patch DOM and update list state locally when returning from Form View
        onWillStart(async () => {
            if (this.env?.inDialog) {
                return;
            }

            const resModel = this.props.resModel;

            if (!cacheService || !cacheService.isReturningFromForm) {
                return;
            }

            // Strictly verify that we are returning to the exact same model
            if (cacheService.sourceModel !== resModel) {
                cacheService.clearFlags();
                return;
            }

            try {
                // Await model readiness to ensure root records are initialized
                if (this.model?.whenReady) {
                    await this.model.whenReady;
                }

                const deletedIds = cacheService.popDeleted(resModel);
                const dirtyIds = cacheService.popDirty(resModel);
                const createdIds = cacheService.popCreated(resModel);
                let hasChanges = false;

                const root = this.model?.root;
                const records = root?.records;

                if (records) {
                    // 1. Handle Deletions using model's internal _removeRecords API
                    if (deletedIds.length > 0) {
                        for (const dId of deletedIds) {
                            const index = records.findIndex((r) => r.resId === dId);
                            if (index !== -1) {
                                if (typeof root._removeRecords === "function") {
                                    root._removeRecords([dId]);
                                } else {
                                    records.splice(index, 1);
                                    if (root.count > 0) {
                                        root.count -= 1;
                                    }
                                }
                                hasChanges = true;
                            }
                        }
                        cacheService.removeCachedRecords(resModel, deletedIds);
                    }

                    // 2. Handle Updates: Reload individual records to preserve Luxon dates,
                    // active field specs, and eval context without reloading the whole table.
                    if (dirtyIds.length > 0) {
                        for (const dId of dirtyIds) {
                            const targetRecord = records.find((r) => r.resId === dId);
                            if (targetRecord) {
                                if (typeof targetRecord._load === "function") {
                                    await targetRecord._load();
                                    hasChanges = true;
                                }
                            }
                        }
                    }

                    // 3. Handle Creations: Reflect newly created records via addExistingRecord
                    if (createdIds.length > 0) {
                        for (const cId of createdIds) {
                            if (!records.some((r) => r.resId === cId)) {
                                if (typeof root.addExistingRecord === "function") {
                                    const newRecord = await root.addExistingRecord(cId, true);
                                    if (newRecord) {
                                        hasChanges = true;
                                    }
                                }
                            }
                        }
                    }

                    // 4. Trigger OWL reactivity update if DOM state changed
                    if (hasChanges) {
                        this.model.notify();
                    }
                }
            } finally {
                // Always reset navigation flags to prevent stuck state
                cacheService.clearFlags();
            }
        });
    },

    /**
     * Intercept record opening from list to establish expected return target.
     */
    async openRecord(record) {
        const cacheService = this.env?.services?.smart_list_cache;
        if (cacheService && !this.env?.inDialog) {
            cacheService.setPendingReturn(this.props.resModel, this.env?.config?.actionId);
        }
        return super.openRecord(...arguments);
    },
});
