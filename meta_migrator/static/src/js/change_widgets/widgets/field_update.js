/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useChange } from "../lib/use_change";
import { FIELD_GROUPS } from "../lib/constants";
import { diffAttrs } from "../lib/parse";
import { Banner } from "../components/banner";
import { TypeBadge, ChangeBadge } from "../components/badges";
import { AttrTable } from "../components/attr_table";

export class MetaFieldUpdate extends Component {
    static template = "meta_migrator.MetaFieldUpdate";
    static components = { Banner, TypeBadge, ChangeBadge, AttrTable };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.c = useChange(this.props);
        const allUnchanged = this.c.changeType === "unchanged" || !this.changedKeys.length;
        this.state = useState({
            showUnchanged: allUnchanged,
        });
    }

    get targetRef() {
        return this.c.targetRef || "";
    }

    get model() {
        const ref = this.targetRef;
        const idx = ref.lastIndexOf(".");
        return idx !== -1 ? ref.slice(0, idx) : "";
    }

    get fname() {
        const ref = this.targetRef;
        const idx = ref.lastIndexOf(".");
        return idx !== -1 ? ref.slice(idx + 1) : ref;
    }

    get banner() {
        const ct = this.c.changeType;
        if (ct === "error") {
            return { level: "danger", title: "Error", text: this.c.message };
        }
        if (ct === "exists") {
            return {
                level: "muted",
                title: "Skipped (Conflict Policy)",
                text: this.c.message || "Field already exists on target; skipped due to conflict policy.",
            };
        }
        if (ct === "unchanged") {
            return {
                level: "muted",
                title: "In Sync",
                text: this.c.message || "Field matches target definition exactly.",
            };
        }
        return {
            level: "warning",
            title: "Update",
            text: this.c.message || "Differing field attributes will be overwritten.",
        };
    }

    get allRows() {
        return diffAttrs(this.c.oldObj || {}, this.c.newObj || {});
    }

    get changedKeys() {
        return this.allRows.filter((r) => r.changed).map((r) => r.key);
    }

    get unchangedCount() {
        return this.allRows.filter((r) => !r.changed).length;
    }

    get groups() {
        const rows = this.allRows;
        const assigned = new Set();
        const res = [];

        for (const g of FIELD_GROUPS) {
            const gRows = rows.filter((r) => g.keys.includes(r.key));
            if (gRows.length) {
                gRows.forEach((r) => assigned.add(r.key));
                res.push({
                    id: g.id,
                    label: g.label,
                    rows: gRows,
                });
            }
        }

        const unassigned = rows.filter((r) => !assigned.has(r.key));
        if (unassigned.length) {
            res.push({
                id: "other",
                label: "Other Attributes",
                rows: unassigned,
            });
        }

        return res;
    }

    get notes() {
        const oldObj = this.c.oldObj || {};
        const newObj = this.c.newObj || {};
        const notes = [];

        if (oldObj.ttype && newObj.ttype && oldObj.ttype !== newObj.ttype) {
            notes.push({
                level: "danger",
                text: `Type change from '${oldObj.ttype}' to '${newObj.ttype}' may cause data loss or schema conflicts.`,
            });
        }
        if (!oldObj.required && newObj.required) {
            notes.push({
                level: "warning",
                text: "Changing 'required' to True may fail if existing records contain null values.",
            });
        }
        if (oldObj.store && newObj.store === false) {
            notes.push({
                level: "warning",
                text: "Changing 'store' to False will drop the database column.",
            });
        }
        if (oldObj.relation && newObj.relation && oldObj.relation !== newObj.relation) {
            notes.push({
                level: "warning",
                text: `Relation model changed from '${oldObj.relation}' to '${newObj.relation}'.`,
            });
        }

        return notes;
    }

    toggleUnchanged() {
        this.state.showUnchanged = !this.state.showUnchanged;
    }

    scrollTo(key) {
        this.state.showUnchanged = true;
        const el = document.getElementById(`attr_row_${key}`);
        if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            el.classList.add("is-flash");
            setTimeout(() => el.classList.remove("is-flash"), 1500);
        }
    }
}

export const metaFieldUpdateField = {
    component: MetaFieldUpdate,
    supportedTypes: ["text"],
};

registry.category("fields").add("meta_field_update", metaFieldUpdateField);
