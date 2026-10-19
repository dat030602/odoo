/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useChange } from "../lib/use_change";
import { Banner } from "../components/banner";
import { BoolPill, TypeBadge, Chip } from "../components/badges";
import { CodeBlock } from "../components/code_block";
import { parseSelection, parseDepends } from "../lib/parse";

export class MetaFieldCreate extends Component {
    static template = "meta_migrator.MetaFieldCreate";
    static components = { Banner, BoolPill, TypeBadge, Chip, CodeBlock };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.c = useChange(this.props);
        this.state = useState({
            helpClamped: true,
        });
    }

    get isError() {
        return this.c.changeType === "error";
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

    get vals() {
        return this.c.newObj || {};
    }

    get parsedSelection() {
        return parseSelection(this.vals.selection);
    }

    get dependsList() {
        return parseDepends(this.vals.depends);
    }

    get groups() {
        const v = this.vals;
        const res = [];

        // 1. Basic Group
        res.push({
            id: "basic",
            label: "Basic",
            wide: false,
            items: [
                { key: "name", label: "Field Name", value: v.name || this.fname },
                { key: "field_description", label: "Label", value: v.field_description || "—" },
                { key: "ttype", label: "Type", value: v.ttype || "—" },
            ],
            help: v.help || null,
        });

        // 2. Constraints Group
        const constraintKeys = ["required", "readonly", "store", "index", "copied", "translate"];
        const flags = constraintKeys.map((k) => ({
            key: k,
            label: k.replace(/_/g, " "),
            value: Boolean(v[k]),
        }));
        res.push({
            id: "constraints",
            label: "Constraints",
            wide: false,
            flags,
        });

        // 3. Relation Group (if relational or has relation key)
        const isRel = ["many2one", "one2many", "many2many"].includes(v.ttype) || Boolean(v.relation);
        if (isRel) {
            res.push({
                id: "relation",
                label: "Relation",
                wide: false,
                items: [
                    { key: "relation", label: "Related Model", value: v.relation || "—" },
                    { key: "relation_field", label: "Relation Field", value: v.relation_field || "—" },
                    { key: "on_delete", label: "On Delete", value: v.on_delete || "—" },
                ],
                domain: v.domain || null,
            });
        }

        // 4. Selection Group
        if (v.ttype === "selection" || v.selection) {
            res.push({
                id: "selection",
                label: "Selection Options",
                wide: true,
                selection: this.parsedSelection,
                rawSelection: typeof v.selection === "string" ? v.selection : null,
            });
        }

        // 5. Logic Group
        if (v.compute || v.depends || v.related) {
            res.push({
                id: "logic",
                label: "Logic",
                wide: true,
                compute: v.compute || null,
                depends: this.dependsList,
                related: v.related || null,
            });
        }

        // 6. Other Keys
        const knownKeys = new Set([
            "name", "field_description", "ttype", "help", "required", "readonly",
            "store", "index", "copied", "translate", "relation", "relation_field",
            "on_delete", "domain", "selection", "compute", "depends", "related"
        ]);
        const otherItems = Object.entries(v)
            .filter(([k]) => !knownKeys.has(k))
            .map(([k, val]) => ({
                key: k,
                label: k.replace(/_/g, " "),
                value: typeof val === "object" ? JSON.stringify(val) : String(val),
            }));

        if (otherItems.length) {
            res.push({
                id: "other",
                label: "Other Attributes",
                wide: false,
                items: otherItems,
            });
        }

        return res;
    }

    toggleHelp() {
        this.state.helpClamped = !this.state.helpClamped;
    }
}

export const metaFieldCreateField = {
    component: MetaFieldCreate,
    supportedTypes: ["text"],
};

registry.category("fields").add("meta_field_create", metaFieldCreateField);
