/** @odoo-module **/

import { Component, useState, useRef } from "@odoo/owl";
import { diffLines, foldOps, changeBlocks, pairRows, stats } from "../lib/diff_algo";
import { tokenize } from "../lib/highlight";

export class CodeDiff extends Component {
    static template = "meta_migrator.CodeDiff";
    static props = {
        old: { type: String, optional: true },
        new: { type: String, optional: true },
        language: { type: String, optional: true },
        mode: { type: String, optional: true },
        ctx: { type: Number, optional: true },
        maxHeight: { type: [Number, String], optional: true },
    };

    setup() {
        this.bodyRef = useRef("body");
        this.state = useState({
            mode: this.props.mode || "unified",
            wrap: false,
            q: "",
            opened: {},
            full: false,
            changeIndex: 0,
            limit: 500,
        });
    }

    get rawOld() {
        return (this.props.old || "").replace(/\r\n|\r/g, "\n");
    }

    get rawNew() {
        return (this.props.new || "").replace(/\r\n|\r/g, "\n");
    }

    get language() {
        return this.props.language || "text";
    }

    get ops() {
        return diffLines(this.rawOld, this.rawNew);
    }

    get stats() {
        return stats(this.ops);
    }

    get blocks() {
        return changeBlocks(this.ops);
    }

    get currentBlockText() {
        const total = this.blocks.length;
        if (!total) return "0 / 0";
        return `${this.state.changeIndex + 1} / ${total}`;
    }

    get unifiedRows() {
        const folded = foldOps(this.ops, this.props.ctx || 3, this.state.opened);
        const lang = this.language;
        const q = (this.state.q || "").toLowerCase();

        return folded.map((r) => {
            if (r.t === "fold") return r;
            return {
                ...r,
                tokens: tokenize(r.text, lang),
                hit: q ? r.text.toLowerCase().includes(q) : false,
            };
        });
    }

    get splitPairs() {
        const pairs = pairRows(this.ops);
        const lang = this.language;
        const q = (this.state.q || "").toLowerCase();

        return pairs.map((p) => {
            const leftTokens = p.left?.wordTokens
                ? p.left.wordTokens.map((wt) => ({
                      t: wt.text,
                      w: wt.w,
                      c: wt.w ? null : tokenize(wt.text, lang)[0]?.c,
                  }))
                : p.left
                ? tokenize(p.left.text, lang)
                : [];

            const rightTokens = p.right?.wordTokens
                ? p.right.wordTokens.map((wt) => ({
                      t: wt.text,
                      w: wt.w,
                      c: wt.w ? null : tokenize(wt.text, lang)[0]?.c,
                  }))
                : p.right
                ? tokenize(p.right.text, lang)
                : [];

            return {
                ...p,
                left: p.left
                    ? {
                          ...p.left,
                          tokens: leftTokens,
                          hit: q ? p.left.text.toLowerCase().includes(q) : false,
                      }
                    : null,
                right: p.right
                    ? {
                          ...p.right,
                          tokens: rightTokens,
                          hit: q ? p.right.text.toLowerCase().includes(q) : false,
                      }
                    : null,
            };
        });
    }

    get visibleUnifiedRows() {
        return this.unifiedRows.slice(0, this.state.limit);
    }

    get visibleSplitPairs() {
        return this.splitPairs.slice(0, this.state.limit);
    }

    get hasMore() {
        const total = this.state.mode === "split" ? this.splitPairs.length : this.unifiedRows.length;
        return total > this.state.limit;
    }

    showMore() {
        this.state.limit += 500;
    }

    setMode(m) {
        this.state.mode = m;
    }

    toggleWrap() {
        this.state.wrap = !this.state.wrap;
    }

    toggleFull() {
        this.state.full = !this.state.full;
    }

    expand(foldId) {
        this.state.opened[foldId] = true;
    }

    expandAll() {
        const ops = this.ops;
        const allOpen = {};
        for (let i = 0; i < ops.length; i++) {
            allOpen[i] = true;
        }
        this.state.opened = allOpen;
        this.state.limit = Math.max(this.state.limit, ops.length);
    }

    copyNew() {
        if (!navigator.clipboard) return;
        try {
            navigator.clipboard.writeText(this.rawNew);
        } catch {
            // Ignore error
        }
    }

    prevChange() {
        const total = this.blocks.length;
        if (!total) return;
        this.state.changeIndex = (this.state.changeIndex - 1 + total) % total;
        this.scrollToBlock(this.state.changeIndex);
    }

    nextChange() {
        const total = this.blocks.length;
        if (!total) return;
        this.state.changeIndex = (this.state.changeIndex + 1) % total;
        this.scrollToBlock(this.state.changeIndex);
    }

    scrollToBlock(idx) {
        const targetOpIndex = this.blocks[idx];
        if (targetOpIndex === undefined) return;
        // Ensure limit reaches this block
        if (targetOpIndex >= this.state.limit) {
            this.state.limit = targetOpIndex + 500;
        }
        if (this.bodyRef.el) {
            const lineH = 20;
            this.bodyRef.el.scrollTop = Math.max(0, targetOpIndex * lineH - 40);
        }
    }
}
