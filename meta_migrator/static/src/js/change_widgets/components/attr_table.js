/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { BoolPill } from "./badges";
import { CodeDiff } from "./code_diff";

export class AttrTable extends Component {
    static template = "meta_migrator.AttrTable";
    static components = { BoolPill, CodeDiff };
    static props = {
        rows: { type: Array, optional: true },
        groups: { type: Array, optional: true },
        showUnchanged: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({
            closed: {},
            diffOpen: {},
            groupExpanded: {},
        });
    }

    get isShowUnchanged() {
        if (this.props.showUnchanged !== undefined) {
            return Boolean(this.props.showUnchanged);
        }
        return false;
    }

    get tableGroups() {
        if (this.props.groups && this.props.groups.length) {
            return this.props.groups;
        }
        return [
            {
                id: "all",
                label: "Attributes",
                rows: this.props.rows || [],
            },
        ];
    }

    toggleGroup(gid) {
        this.state.closed[gid] = !this.state.closed[gid];
        // If user explicitly expands an individual group, show its attributes
        if (!this.state.closed[gid]) {
            this.state.groupExpanded[gid] = true;
        } else {
            this.state.groupExpanded[gid] = false;
        }
    }

    isRowVisible(row, gid) {
        if (row.changed) return true;
        if (this.isShowUnchanged) return true;
        if (this.state.groupExpanded[gid]) return true;
        return false;
    }

    toggleDiff(key) {
        this.state.diffOpen[key] = !this.state.diffOpen[key];
    }

    isBool(val) {
        return typeof val === "boolean";
    }

    isLongText(val) {
        if (typeof val !== "string") return false;
        return val.length > 120 || val.includes("\n");
    }

    formatVal(val) {
        if (val === null || val === undefined || val === "") {
            return "—";
        }
        if (typeof val === "object") {
            try {
                return JSON.stringify(val);
            } catch {
                return String(val);
            }
        }
        return String(val);
    }
}
