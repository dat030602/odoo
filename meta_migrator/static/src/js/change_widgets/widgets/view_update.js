/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useChange } from "../lib/use_change";
import { diffLines } from "../lib/diff_algo";
import { Banner } from "../components/banner";
import { CodeBlock } from "../components/code_block";
import { CodeDiff } from "../components/code_diff";

export class MetaViewUpdate extends Component {
    static template = "meta_migrator.MetaViewUpdate";
    static components = { Banner, CodeBlock, CodeDiff };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.c = useChange(this.props);
        const hasAdded = Boolean(this.extra.added && this.extra.added.length > 0);
        this.state = useState({
            tab: hasAdded ? "change" : "diff",
        });
    }

    get extra() {
        return this.c.extra || {};
    }

    get added() {
        const raw = this.extra.added || [];
        return raw.map((xml) => {
            const lines = xml.trim().split("\n");
            const firstLine = lines[0] || "";
            const title = firstLine.length > 120 ? firstLine.slice(0, 117) + "..." : firstLine;
            return {
                title,
                xml,
                lines: lines.length,
            };
        });
    }

    get present() {
        return this.extra.present || [];
    }

    get addedLines() {
        const ops = diffLines(this.c.oldRaw, this.c.newRaw);
        const set = new Set();
        for (const op of ops) {
            if (op.t === "add" && op.b) {
                set.add(op.b);
            }
        }
        return set;
    }

    get subtitle() {
        const count = this.added.length;
        const wrapped = this.extra.wrapped ? " (wrapped in <data>)" : "";
        if (count > 0) {
            return `Appending ${count} element${count > 1 ? "s" : ""} to <data>${wrapped}`;
        }
        return this.c.message || "";
    }

    get banner() {
        const ct = this.c.changeType;
        if (ct === "error") {
            return { level: "danger", title: "Error", text: this.c.message };
        }
        if (ct === "unchanged") {
            return {
                level: "muted",
                title: "In Sync",
                text: this.c.message || "All elements are already present in target view arch (in sync).",
            };
        }
        return null;
    }

    get tabs() {
        const res = [];
        if (this.added.length > 0) {
            res.push({ id: "change", label: "Change", badge: this.added.length });
        }
        res.push({ id: "diff", label: "Diff" });
        if (this.c.oldRaw) {
            res.push({ id: "current", label: "Current (target)" });
        }
        if (this.c.newRaw) {
            res.push({ id: "result", label: "Result" });
        }
        return res;
    }

    setTab(t) {
        this.state.tab = t;
    }

    copy(text) {
        if (!navigator.clipboard) return;
        try {
            navigator.clipboard.writeText(text);
        } catch {
            // Ignore error
        }
    }
}

export const metaViewUpdateField = {
    component: MetaViewUpdate,
    supportedTypes: ["text"],
};

registry.category("fields").add("meta_view_update", metaViewUpdateField);
