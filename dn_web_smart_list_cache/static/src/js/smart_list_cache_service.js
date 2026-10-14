/** @odoo-module **/

import { registry } from "@web/core/registry";

const MAX_CACHE_ENTRIES = 20;
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Sanitize a server record to guarantee it only contains plain JSON data
 * and never contains OWL Datapoint / StaticList objects that crash _parseServerValues.
 */
function sanitizeServerRecord(rawRecord) {
    if (!rawRecord || typeof rawRecord !== "object") {
        return rawRecord;
    }
    const clean = {};
    for (const [k, v] of Object.entries(rawRecord)) {
        if (v && typeof v === "object") {
            if (Array.isArray(v)) {
                clean[k] = [...v];
            } else if (v.constructor === Object) {
                clean[k] = { ...v };
            } else if (v.records && Array.isArray(v.records)) {
                // If a StaticList was somehow provided, extract raw IDs
                clean[k] = v.records.map((sub) => sub.resId || sub.id);
            } else if ("id" in v) {
                // Many2one or similar datapoint
                clean[k] = [v.id, v.display_name || v.name || ""];
            } else {
                continue;
            }
        } else {
            clean[k] = v;
        }
    }
    return clean;
}

/**
 * Global cache service to track record modifications during navigation
 * and manage cached list view states with compound keys and LRU eviction.
 */
export const smartListCacheService = {
    start() {
        const dirtyRecords = {};   // { [resModel]: Set<resId> }
        const deletedRecords = {}; // { [resModel]: Set<resId> }
        const createdRecords = {}; // { [resModel]: Set<resId> }
        const cachedData = new Map(); // key -> { records: Object[], length: number, timestamp: number }

        return {
            // Navigation state flags
            isReturningFromForm: false,
            sourceModel: null,
            sourceActionId: null,
            expectedReturnModel: null,
            expectedReturnActionId: null,

            setPendingReturn(resModel, actionId) {
                this.expectedReturnModel = resModel;
                this.expectedReturnActionId = actionId;
            },

            clearFlags() {
                this.isReturningFromForm = false;
                this.sourceModel = null;
                this.sourceActionId = null;
                this.expectedReturnModel = null;
                this.expectedReturnActionId = null;
            },

            // -- Compound Key Generation --
            buildCacheKey(config, env) {
                const actionId = env?.config?.actionId || "default";
                const resModel = config.resModel;
                const domainStr = JSON.stringify(config.domain || []);
                const offset = config.offset || 0;
                const limit = config.limit || 80;
                const orderByStr = JSON.stringify(config.orderBy || []);
                return `${actionId}:${resModel}:${offset}:${limit}:${domainStr}:${orderByStr}`;
            },

            // -- Update (Dirty) Tracking --
            markDirty(resModel, resId) {
                if (!resModel || !resId) {
                    return;
                }
                if (!dirtyRecords[resModel]) {
                    dirtyRecords[resModel] = new Set();
                }
                dirtyRecords[resModel].add(resId);
            },
            popDirty(resModel) {
                const records = Array.from(dirtyRecords[resModel] || []);
                dirtyRecords[resModel] = new Set();
                return records;
            },

            // -- Deletion Tracking --
            markDeleted(resModel, resId) {
                if (!resModel || !resId) {
                    return;
                }
                if (!deletedRecords[resModel]) {
                    deletedRecords[resModel] = new Set();
                }
                deletedRecords[resModel].add(resId);

                // Purge from dirty and created sets
                dirtyRecords[resModel]?.delete(resId);
                createdRecords[resModel]?.delete(resId);
            },
            popDeleted(resModel) {
                const records = Array.from(deletedRecords[resModel] || []);
                deletedRecords[resModel] = new Set();
                return records;
            },

            // -- Creation (New Record) Tracking --
            markCreated(resModel, resId) {
                if (!resModel || !resId) {
                    return;
                }
                if (!createdRecords[resModel]) {
                    createdRecords[resModel] = new Set();
                }
                createdRecords[resModel].add(resId);
                // Ensure not marked dirty to avoid duplicate RPC calls
                dirtyRecords[resModel]?.delete(resId);
            },
            popCreated(resModel) {
                const records = Array.from(createdRecords[resModel] || []);
                createdRecords[resModel] = new Set();
                return records;
            },

            // -- List Data Caching with LRU and TTL --
            setCachedData(cacheKey, data) {
                if (!cacheKey || !data || !Array.isArray(data.records)) {
                    return;
                }

                // Evict oldest if reaching capacity
                if (cachedData.size >= MAX_CACHE_ENTRIES) {
                    const oldestKey = cachedData.keys().next().value;
                    cachedData.delete(oldestKey);
                }

                // Sanitize records to pure server JSON
                const cleanRecords = data.records.map((r) => sanitizeServerRecord(r));

                cachedData.set(cacheKey, {
                    records: cleanRecords,
                    length: typeof data.length === "number" ? data.length : cleanRecords.length,
                    timestamp: Date.now(),
                });
            },

            getCachedData(cacheKey) {
                const entry = cachedData.get(cacheKey);
                if (!entry) {
                    return null;
                }

                // Check TTL
                if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
                    cachedData.delete(cacheKey);
                    return null;
                }

                // Re-insert to keep MRU order
                cachedData.delete(cacheKey);
                cachedData.set(cacheKey, entry);

                return {
                    records: entry.records.map((r) => ({ ...r })),
                    length: entry.length,
                };
            },

            hasCachedData(cacheKey) {
                const entry = cachedData.get(cacheKey);
                if (!entry) {
                    return false;
                }
                if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
                    cachedData.delete(cacheKey);
                    return false;
                }
                return true;
            },

            updateCachedRecords(resModel, updatedRecords) {
                if (!Array.isArray(updatedRecords)) {
                    return;
                }
                const updatedMap = new Map(updatedRecords.map((r) => [r.id, sanitizeServerRecord(r)]));

                for (const [key, entry] of cachedData.entries()) {
                    if (key.includes(`:${resModel}:`)) {
                        for (let i = 0; i < entry.records.length; i++) {
                            const recId = entry.records[i].id;
                            if (updatedMap.has(recId)) {
                                Object.assign(entry.records[i], updatedMap.get(recId));
                            }
                        }
                    }
                }
            },

            removeCachedRecords(resModel, deletedIds) {
                if (!Array.isArray(deletedIds) || !deletedIds.length) {
                    return;
                }
                const idSet = new Set(deletedIds);

                for (const [key, entry] of cachedData.entries()) {
                    if (key.includes(`:${resModel}:`)) {
                        entry.records = entry.records.filter((r) => !idSet.has(r.id));
                        entry.length = Math.max(0, entry.length - deletedIds.length);
                    }
                }
            },

            addCachedRecords(resModel, newRecords) {
                if (!Array.isArray(newRecords) || !newRecords.length) {
                    return;
                }
                for (const [key, entry] of cachedData.entries()) {
                    if (key.includes(`:${resModel}:`)) {
                        for (const rec of newRecords) {
                            if (!entry.records.some((r) => r.id === rec.id)) {
                                entry.records.unshift(sanitizeServerRecord(rec));
                                entry.length += 1;
                            }
                        }
                    }
                }
            },

            // -- Cleanup --
            clear(resModel) {
                if (resModel) {
                    delete dirtyRecords[resModel];
                    delete deletedRecords[resModel];
                    delete createdRecords[resModel];
                    for (const key of cachedData.keys()) {
                        if (key.includes(`:${resModel}:`)) {
                            cachedData.delete(key);
                        }
                    }
                } else {
                    Object.keys(dirtyRecords).forEach((k) => delete dirtyRecords[k]);
                    Object.keys(deletedRecords).forEach((k) => delete deletedRecords[k]);
                    Object.keys(createdRecords).forEach((k) => delete createdRecords[k]);
                    cachedData.clear();
                }
            },
        };
    },
};

// Register in Odoo services registry (both canonical name and alias)
registry.category("services").add("smart_list_cache", smartListCacheService);
registry.category("services").add("dn_smart_list_cache", smartListCacheService);
