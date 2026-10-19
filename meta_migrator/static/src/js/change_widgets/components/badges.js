/** @odoo-module **/

import { Component } from "@odoo/owl";
import { getTypeGroup } from "../lib/constants";

export class BoolPill extends Component {
    static template = "meta_migrator.BoolPill";
    static props = {
        value: { type: Boolean, optional: true },
    };
}

export class TypeBadge extends Component {
    static template = "meta_migrator.TypeBadge";
    static props = {
        ttype: { type: String, optional: true },
    };

    get group() {
        return getTypeGroup(this.props.ttype || "");
    }
}

export class ChangeBadge extends Component {
    static template = "meta_migrator.ChangeBadge";
    static props = {
        type: { type: String, optional: true },
        label: { type: String, optional: true },
    };

    get label() {
        return this.props.label || this.props.type || "";
    }
}

export class Chip extends Component {
    static template = "meta_migrator.Chip";
    static props = {
        text: { type: String },
        cls: { type: String, optional: true },
    };
}
