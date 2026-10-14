/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { RelationalModel } from "@web/model/relational_model/relational_model";

patch(RelationalModel.prototype, {
    /**
     * Intercept data loading for ungrouped root lists to bypass server search_read
     * when navigating back from Form View.
     */
    async _loadData(config, cache) {
        const cacheService = this.env?.services?.smart_list_cache;
        const resModel = config.resModel;

        // Strictly target root ungrouped list views: ignore subviews (One2many/Many2many), dialogs, and grouped lists
        const isMainUngroupedList =
            !this.env?.inDialog &&
            this.env?.config?.viewType === "list" &&
            !config.isMonoRecord &&
            (!config.groupBy || !config.groupBy.length);

        if (isMainUngroupedList && cacheService) {
            const cacheKey = cacheService.buildCacheKey(config, this.env);

            if (
                cacheService.isReturningFromForm &&
                cacheService.sourceModel === resModel &&
                (!cacheService.sourceActionId || cacheService.sourceActionId === this.env?.config?.actionId) &&
                cacheService.hasCachedData(cacheKey)
            ) {
                // Restore from cached clean server data: ZERO network queries executed
                return cacheService.getCachedData(cacheKey);
            }
        }

        const data = await super._loadData(...arguments);

        // Cache loaded clean list data using compound key for subsequent back navigation
        if (isMainUngroupedList && cacheService && data?.records) {
            const cacheKey = cacheService.buildCacheKey(config, this.env);
            cacheService.setCachedData(cacheKey, data);
        }

        return data;
    },
});
