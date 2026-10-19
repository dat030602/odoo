/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useChange } from "../lib/use_change";
import { MODEL_FIELDS_COLUMNS } from "../lib/constants";
import { Banner } from "../components/banner";
import { BoolPill, TypeBadge } from "../components/badges";
import { CodeBlock } from "../components/code_block";
import { parseSelection, parseDepends } from "../lib/parse";

export class MetaModelCreate extends Component {
    static template = "meta_migrator.MetaModelCreate";
    static components = { Banner, BoolPill, TypeBadge, CodeBlock };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.c = useChange(this.props);

        const initialCols = {};
        for (const col of MODEL_FIELDS_COLUMNS) {
            initialCols[col.key] = col.defaultVisible;
        }

        this.state = useState({
            q: "",
            types: {},
            onlyErrors: false,
            onlyRequired: false,
            colVisibility: initialCols,
            open: {},
            limit: 100,
        });
    }

    get isError() {
        return this.c.changeType === "error";
    }

    get modelObj() {
        return this.c.newObj || {};
    }

    get renamedFrom() {
        return this.c.extra?.source_model || null;
    }

    get allColumns() {
        return MODEL_FIELDS_COLUMNS.map((col) => ({
            ...col,
            visible: this.state.colVisibility[col.key],
        }));
    }

    get columns() {
        return this.allColumns.filter((c) => c.visible);
    }

    get rawChildren() {
        return this.c.children || [];
    }

    get typeChips() {
        const set = new Set();
        for (const ch of this.rawChildren) {
            const t = ch.vals?.ttype;
            if (t) set.add(t);
        }
        return Array.from(set).sort();
    }

    get rows() {
        const q = (this.state.q || "").toLowerCase().trim();
        const activeTypes = Object.entries(this.state.types)
            .filter(([_, on]) => on)
            .map(([t]) => t);
        const onlyErrors = this.state.onlyErrors;
        const onlyReq = this.state.onlyRequired;

        return this.rawChildren
            .map((ch) => {
                const vals = ch.vals || {};
                const name = ch.name || vals.name || "";
                const desc = vals.field_description || "";
                const ttype = vals.ttype || "";
                const isErr = ch.change_type === "error" || Boolean(ch.error);
                const isReq = Boolean(vals.required);

                return {
                    id: ch.id || name,
                    name,
                    field_description: desc,
                    ttype,
                    vals,
                    error: isErr,
                    message: ch.message || "",
                    required: isReq,
                    store: Boolean(vals.store),
                    relation: vals.relation || "",
                    compute: vals.compute ? vals.compute.split("\n")[0] : "",
                    readonly: Boolean(vals.readonly),
                    index: Boolean(vals.index),
                    copied: Boolean(vals.copied),
                    translate: Boolean(vals.translate),
                    relation_field: vals.relation_field || "",
                    on_delete: vals.on_delete || "",
                    depends: parseDepends(vals.depends),
                    related: vals.related || "",
                    selection: parseSelection(vals.selection),
                    rawSelection: typeof vals.selection === "string" ? vals.selection : "",
                    help: vals.help || "",
                    domain: vals.domain || "",
                };
            })
            .filter((r) => {
                if (q && !r.name.toLowerCase().includes(q) && !r.field_description.toLowerCase().includes(q)) {
                    return false;
                }
                if (activeTypes.length && !activeTypes.includes(r.ttype)) {
                    return false;
                }
                if (onlyErrors && !r.error) {
                    return false;
                }
                if (onlyReq && !r.required) {
                    return false;
                }
                return true;
            });
    }

    get visibleRows() {
        return this.rows.slice(0, this.state.limit);
    }

    get hasMore() {
        return this.rows.length > this.state.limit;
    }

    get errCount() {
        return this.rawChildren.filter((c) => c.change_type === "error").length;
    }

    get reqCount() {
        return this.rawChildren.filter((c) => c.vals?.required).length;
    }

    showMore() {
        this.state.limit += 100;
    }

    toggleType(t) {
        this.state.types[t] = !this.state.types[t];
    }

    toggleErrors() {
        this.state.onlyErrors = !this.state.onlyErrors;
    }

    toggleCol(key) {
        this.state.colVisibility[key] = !this.state.colVisibility[key];
    }

    toggleRow(id) {
        this.state.open[id] = !this.state.open[id];
    }

    expandAll() {
        const next = {};
        const openAll = Object.keys(this.state.open).length === 0;
        if (openAll) {
            for (const r of this.rows) {
                next[r.id] = true;
            }
        }
        this.state.open = next;
    }

    onRowKey(ev, id) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            this.toggleRow(id);
        }
    }
}

export const metaModelCreateField = {
    component: MetaModelCreate,
    supportedTypes: ["text"],
};

registry.category("fields").add("meta_model_create", metaModelCreateField);
