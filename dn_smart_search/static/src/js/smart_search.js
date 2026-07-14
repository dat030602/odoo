/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useService } from "@web/core/utils/hooks";
import { KeepLast } from "@web/core/utils/concurrency";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup, Component, useRef, useState } from "@odoo/owl";

function highlightText(text, keyword) {
    const value = String(text || "");
    const search = String(keyword || "").trim();
    if (!search) {
        return markup(value);
    }
    const escaped = search.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return markup(value.replace(new RegExp(`(${escaped})`, "ig"), "<mark>$1</mark>"));
}

class SmartSearchDialog extends Component {
    static template = "dn_smart_search.SmartSearchDialog";
    static components = { Dialog };
    static props = { close: Function };

    setup() {
        this.action = useService("action");
        this.keepLast = new KeepLast();
        this.inputRef = useRef("smartSearchInput");
        this.state = useState({
            query: "",
            loading: false,
            results: [],
            selectedIndex: -1,
        });

        useHotkey("Escape", () => this.props.close(), {
            global: true,
            bypassEditableProtection: true,
        });
        useHotkey("ArrowDown", () => this.moveSelection(1), {
            global: true,
            bypassEditableProtection: true,
            allowRepeat: true,
        });
        useHotkey("ArrowUp", () => this.moveSelection(-1), {
            global: true,
            bypassEditableProtection: true,
            allowRepeat: true,
        });
        useHotkey("Enter", () => this.openSelected(), {
            global: true,
            bypassEditableProtection: true,
        });
        useHotkey("control+k", () => this.inputRef.el?.focus(), {
            global: true,
            bypassEditableProtection: true,
        });
    }

    async onInput(ev) {
        const query = ev.target.value;
        this.state.query = query;
        this.state.loading = true;
        const results = await this.keepLast.add(this.fetchResults(query));
        this.state.results = results;
        this.state.selectedIndex = results.length ? 0 : -1;
        this.state.loading = false;
    }

    async fetchResults(query) {
        const trimmed = query.trim();
        if (!trimmed) {
            return [];
        }
        const response = await rpc("/smart/search", { keyword: trimmed, limit: 20 });
        return response.results || [];
    }

    moveSelection(delta) {
        const count = this.state.results.length;
        if (!count) {
            return;
        }
        if (this.state.selectedIndex < 0) {
            this.state.selectedIndex = 0;
            return;
        }
        this.state.selectedIndex = (this.state.selectedIndex + delta + count) % count;
    }

    openSelected(index = this.state.selectedIndex) {
        const result = this.state.results[index];
        if (!result) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: result.display,
            res_model: result.model,
            res_id: result.id,
            views: [[false, "form"]],
            target: "current",
        });
        this.props.close();
    }

    onResultMouseEnter(index) {
        this.state.selectedIndex = index;
    }

    get renderedResults() {
        return this.state.results.map((result) => ({
            ...result,
            displayHtml: highlightText(result.display, this.state.query),
            subtitleHtml: highlightText(result.subtitle, this.state.query),
        }));
    }
}

class SmartSearchSystray extends Component {
    static template = "dn_smart_search.SmartSearchSystray";
    setup() {
        this.dialog = useService("dialog");
        useHotkey("control+k", () => this.dialog.add(SmartSearchDialog, {}), {
            global: true,
            bypassEditableProtection: true,
        });
    }

    onClick() {
        this.dialog.add(SmartSearchDialog, {});
    }
}

registry.category("systray").add(
    "dn_smart_search",
    { Component: SmartSearchSystray },
    { sequence: 0.5, force: true }
);
