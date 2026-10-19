/** @odoo-module **/

import { Component, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useChange } from "../lib/use_change";
import { xmlWellFormed, scanXmlTags } from "../lib/parse";
import { Banner } from "../components/banner";
import { TypeBadge } from "../components/badges";
import { CodeBlock } from "../components/code_block";

export class MetaViewCreate extends Component {
    static template = "meta_migrator.MetaViewCreate";
    static components = { Banner, TypeBadge, CodeBlock };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.c = useChange(this.props);
        this.codeBlockRef = useRef("codeBlock");
        this.state = useState({
            showOutline: true,
        });
    }

    get isError() {
        return this.c.changeType === "error";
    }

    get extra() {
        const ext = this.c.extra || {};
        if (ext.name || ext.type || ext.model) {
            return ext;
        }
        // Fallback deduction from targetRef or name
        const match = (this.props.record.data.name || "").match(/^view (\S+) on (\S+)$/);
        return {
            name: "—",
            type: match ? match[1] : "—",
            model: match ? match[2] : this.c.targetRef || "—",
            priority: 16,
            inherit_name: null,
        };
    }

    get validation() {
        return xmlWellFormed(this.c.newRaw);
    }

    get outline() {
        if (!this.c.newRaw) return [];
        const tags = scanXmlTags(this.c.newRaw);
        return tags.filter((t) => t.depth <= 3).slice(0, 300);
    }

    toggleOutline() {
        this.state.showOutline = !this.state.showOutline;
    }

    goto(line) {
        if (this.codeBlockRef.comp) {
            this.codeBlockRef.comp.scrollToLine(line);
        }
    }
}

export const metaViewCreateField = {
    component: MetaViewCreate,
    supportedTypes: ["text"],
};

registry.category("fields").add("meta_view_create", metaViewCreateField);
