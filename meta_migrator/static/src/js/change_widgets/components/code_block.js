/** @odoo-module **/

import { Component, useState, useRef } from "@odoo/owl";
import { tokenize } from "../lib/highlight";
import { scanXmlTags } from "../lib/parse";

export class CodeBlock extends Component {
    static template = "meta_migrator.CodeBlock";
    static props = {
        text: { type: String, optional: true },
        language: { type: String, optional: true },
        mark: { type: String, optional: true },
        maxHeight: { type: [Number, String], optional: true },
        wrap: { type: Boolean, optional: true },
        title: { type: String, optional: true },
        foldNodes: { type: Boolean, optional: true },
        markedLines: { type: [Object, Array], optional: true },
    };

    setup() {
        this.bodyRef = useRef("body");
        this.state = useState({
            full: false,
            wrap: Boolean(this.props.wrap),
            q: "",
            collapsed: {},
        });
    }

    get rawText() {
        return (this.props.text || "").replace(/\r\n|\r/g, "\n");
    }

    get language() {
        return this.props.language || "text";
    }

    get tagsMap() {
        if (!this.props.foldNodes || this.language !== "xml") return {};
        const tags = scanXmlTags(this.rawText);
        const map = {};
        for (const t of tags) {
            if (t.foldable && t.endLine > t.line) {
                map[t.line] = t;
            }
        }
        return map;
    }

    get allLines() {
        const text = this.rawText;
        if (!text) return [];
        const lines = text.split("\n");
        const lang = this.language;
        const q = (this.state.q || "").toLowerCase();
        const tags = this.tagsMap;
        const marked = this.props.markedLines;

        return lines.map((l, idx) => {
            const n = idx + 1;
            const tagInfo = tags[n];
            const isMarked =
                this.props.mark === "add" ||
                (marked && (marked.has ? marked.has(n) : Array.isArray(marked) && marked.includes(n)));
            const isDel = this.props.mark === "del";

            return {
                n,
                text: l,
                tokens: tokenize(l, lang),
                mark: isMarked ? "add" : isDel ? "del" : null,
                hit: q ? l.toLowerCase().includes(q) : false,
                foldable: Boolean(tagInfo),
                endLine: tagInfo ? tagInfo.endLine : n,
            };
        });
    }

    get visibleLines() {
        const lines = this.allLines;
        if (!this.props.foldNodes || this.language !== "xml") {
            return lines;
        }

        const out = [];
        let skipUntil = -1;

        for (const ln of lines) {
            if (skipUntil > 0 && ln.n <= skipUntil) {
                continue;
            }
            if (this.state.collapsed[ln.n] && ln.foldable) {
                out.push({
                    ...ln,
                    collapsed: true,
                });
                skipUntil = ln.endLine;
            } else {
                out.push({
                    ...ln,
                    collapsed: false,
                });
            }
        }
        return out;
    }

    toggleWrap() {
        this.state.wrap = !this.state.wrap;
    }

    toggleFull() {
        this.state.full = !this.state.full;
    }

    toggleNode(lineNum) {
        this.state.collapsed[lineNum] = !this.state.collapsed[lineNum];
    }

    copy() {
        if (!navigator.clipboard) return;
        try {
            navigator.clipboard.writeText(this.rawText);
        } catch {
            // Ignore error in restricted contexts
        }
    }

    scrollToLine(lineNum) {
        if (this.bodyRef.el) {
            const lineH = 20; // 20px line height
            this.bodyRef.el.scrollTop = Math.max(0, (lineNum - 1) * lineH - 40);
        }
    }
}
