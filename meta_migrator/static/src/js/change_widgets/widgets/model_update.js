/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useChange } from "../lib/use_change";
import { diffAttrs } from "../lib/parse";
import { Banner } from "../components/banner";

export class MetaModelUpdate extends Component {
    static template = "meta_migrator.MetaModelUpdate";
    static components = { Banner };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.c = useChange(this.props);
        this.state = useState({
            onlyChanged: false,
        });
    }

    get banner() {
        const ct = this.c.changeType;
        if (ct === "error") {
            return { level: "danger", title: "Error", text: this.c.message };
        }
        if (ct === "update") {
            return {
                level: "warning",
                title: "Model Update",
                text: this.c.message || "Model attributes will be updated.",
            };
        }
        if (ct === "exists") {
            return {
                level: "muted",
                title: "Skipped",
                text: this.c.message || "Model already exists at target. Attributes differ, but model updates are skipped.",
            };
        }
        return {
            level: "muted",
            title: "In Sync",
            text: this.c.message || "Model already exists at target (in sync).",
        };
    }

    get rows() {
        const keys = ["model", "name", "state", "transient"];
        const oldObj = this.c.oldObj || {};
        const newObj = this.c.newObj || {};
        const diffs = diffAttrs(oldObj, newObj, keys);

        return diffs.map((d) => ({
            ...d,
            old: typeof d.old === "boolean" ? (d.old ? "True" : "False") : d.old ?? "—",
            new: typeof d.new === "boolean" ? (d.new ? "True" : "False") : d.new ?? "—",
        }));
    }

    get diffCount() {
        return this.rows.filter((r) => r.changed).length;
    }

    toggleOnly() {
        this.state.onlyChanged = !this.state.onlyChanged;
    }
}

export const metaModelUpdateField = {
    component: MetaModelUpdate,
    supportedTypes: ["text"],
};

registry.category("fields").add("meta_model_update", metaModelUpdateField);
