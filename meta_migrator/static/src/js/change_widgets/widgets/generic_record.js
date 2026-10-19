/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useChange } from "../lib/use_change";
import { diffAttrs } from "../lib/parse";
import { Banner } from "../components/banner";
import { BoolPill, Chip } from "../components/badges";
import { CodeBlock } from "../components/code_block";
import { AttrTable } from "../components/attr_table";

export class MetaGenericRecord extends Component {
    static template = "meta_migrator.MetaGenericRecord";
    static components = { Banner, BoolPill, Chip, CodeBlock, AttrTable };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.c = useChange(this.props);
        this.state = useState({
            showUnchanged: false,
        });
    }

    get isCreate() {
        return !this.c.oldRaw || this.c.changeType === "create";
    }

    get isError() {
        return this.c.changeType === "error";
    }

    get kind() {
        const ot = this.c.objectType;
        if (ot === "menu") {
            const name = this.props.record.data.name || "";
            return name.startsWith("window action:") ? "window_action" : "menu";
        }
        return ot; // 'access_right' or 'record_rule'
    }

    get kindLabel() {
        switch (this.kind) {
            case "access_right":
                return "Access Control";
            case "record_rule":
                return "Record Rule";
            case "window_action":
                return "Window Action";
            case "menu":
                return "Menu Item";
            default:
                return "Record";
        }
    }

    get title() {
        return this.props.record.data.name || this.c.targetRef;
    }

    get banner() {
        if (this.isError) {
            return { level: "danger", title: "Error", text: this.c.message };
        }
        if (!this.c.newRaw && !this.c.oldRaw) {
            return {
                level: "muted",
                title: "Empty",
                text: this.c.message || "No record data available.",
            };
        }
        if (this.c.changeType === "exists") {
            return {
                level: "muted",
                title: "Skipped",
                text: this.c.message || "Record exists and is skipped due to policy.",
            };
        }
        return null;
    }

    get perms() {
        const obj = this.c.newObj || {};
        return [
            { key: "perm_read", label: "Read", on: Boolean(obj.perm_read) },
            { key: "perm_write", label: "Write", on: Boolean(obj.perm_write) },
            { key: "perm_create", label: "Create", on: Boolean(obj.perm_create) },
            { key: "perm_unlink", label: "Delete", on: Boolean(obj.perm_unlink) },
        ];
    }

    get kvItems() {
        const obj = this.c.newObj || {};
        const entries = Object.entries(obj);
        return entries.map(([k, val]) => {
            const isB = typeof val === "boolean";
            const isCode = typeof val === "string" && (val.length > 80 || val.includes("\n") || val.startsWith("[") || val.startsWith("{"));
            return {
                key: k,
                label: k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
                value: val,
                isBool: isB,
                isCode,
            };
        });
    }

    get rows() {
        return diffAttrs(this.c.oldObj || {}, this.c.newObj || {});
    }

    get groups() {
        return [
            {
                id: "all",
                label: "Attributes",
                rows: this.rows,
            },
        ];
    }
}

export const metaGenericRecordField = {
    component: MetaGenericRecord,
    supportedTypes: ["text"],
};

registry.category("fields").add("meta_generic_record", metaGenericRecordField);
