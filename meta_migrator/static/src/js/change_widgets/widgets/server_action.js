/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useChange } from "../lib/use_change";
import { parseServerAction, norm } from "../lib/parse";
import { Banner } from "../components/banner";
import { CodeBlock } from "../components/code_block";
import { CodeDiff } from "../components/code_diff";

export class MetaServerAction extends Component {
    static template = "meta_migrator.MetaServerAction";
    static components = { Banner, CodeBlock, CodeDiff };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.c = useChange(this.props);
    }

    get isCreate() {
        return !this.c.oldRaw || this.c.changeType === "create";
    }

    get isError() {
        return this.c.changeType === "error";
    }

    get newParsed() {
        return parseServerAction(this.c.newRaw);
    }

    get oldParsed() {
        return parseServerAction(this.c.oldRaw);
    }

    get banner() {
        if (this.isError) {
            return { level: "danger", title: "Error", text: this.c.message };
        }
        if (this.c.newRaw && !this.newParsed.hasSeparator) {
            return {
                level: "warning",
                title: "Warning",
                text: "No '--- code ---' separator found. Showing entire text as code.",
            };
        }
        return null;
    }

    get cfg() {
        const keys = [
            { key: "name", label: "Action Name" },
            { key: "state", label: "Action Type" },
            { key: "model", label: "Model" },
            { key: "binding_model", label: "Context Model" },
            { key: "binding_type", label: "Context Type" },
        ];

        const oldHead = this.oldParsed.head || {};
        const newHead = this.newParsed.head || {};

        return keys.map(({ key, label }) => {
            const oldVal = oldHead[key] || "";
            const newVal = newHead[key] || "";
            const changed = norm(oldVal) !== norm(newVal);

            return {
                key,
                label,
                old: oldVal,
                new: newVal,
                changed,
            };
        });
    }

    get noCode() {
        const state = this.newParsed.head.state;
        const code = (this.newParsed.code || "").trim();
        return state && state !== "code" && !code;
    }

    get hasCodeDiff() {
        const oldCode = (this.oldParsed.code || "").trim();
        const newCode = (this.newParsed.code || "").trim();
        return oldCode !== newCode;
    }
}

export const metaServerActionField = {
    component: MetaServerAction,
    supportedTypes: ["text"],
};

registry.category("fields").add("meta_server_action", metaServerActionField);
