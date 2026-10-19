/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState } from "@odoo/owl";
import { diffLines } from "./diff_algo";

const CONTEXT = 3;

export class MetaDiffField extends Component {
    static template = "meta_migrator.MetaDiffField";
    static props = {
        ...standardFieldProps,
        oldField: { type: String, optional: true },
    };

    setup() {
        this.state = useState({ open: {} });
    }

    get ops() {
        const data = this.props.record.data;
        const oldVal = (this.props.oldField && data[this.props.oldField]) || "";
        const newVal = data[this.props.name] || "";
        return diffLines(oldVal, newVal);
    }

    get stats() {
        const ops = this.ops;
        return {
            added: ops.filter((o) => o.t === "add").length,
            removed: ops.filter((o) => o.t === "del").length,
        };
    }

    get rows() {
        const ops = this.ops;
        const keep = new Array(ops.length).fill(false);
        ops.forEach((o, i) => {
            if (o.t !== "eq") {
                for (let k = Math.max(0, i - CONTEXT); k <= Math.min(ops.length - 1, i + CONTEXT); k++) {
                    keep[k] = true;
                }
            }
        });
        const rows = [];
        for (let i = 0; i < ops.length; i++) {
            if (keep[i] || this.state.open[i] || !ops.some((o) => o.t !== "eq")) {
                rows.push(ops[i]);
                continue;
            }
            let j = i;
            while (j < ops.length && !keep[j]) {
                j++;
            }
            rows.push({ t: "fold", id: i, count: j - i });
            i = j - 1;
        }
        return rows;
    }

    expand(id) {
        this.state.open[id] = true;
    }

    copyRaw() {
        const raw = this.props.record.data[this.props.name] || "";
        navigator.clipboard.writeText(raw);
    }
}

export const metaDiffField = {
    component: MetaDiffField,
    supportedTypes: ["text", "char", "html"],
    extractProps: ({ options }) => ({
        oldField: options?.old_field,
    }),
};

registry.category("fields").add("meta_diff", metaDiffField);
