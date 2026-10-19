/** @odoo-module **/

import { Component } from "@odoo/owl";

export class Banner extends Component {
    static template = "meta_migrator.Banner";
    static props = {
        level: { type: String, optional: true },
        title: { type: String, optional: true },
        text: { type: String, optional: true },
    };

    get level() {
        return this.props.level || "info";
    }

    get icon() {
        switch (this.level) {
            case "danger":
                return "⚠";
            case "warning":
                return "!";
            case "muted":
                return "–";
            case "info":
            default:
                return "i";
        }
    }
}
