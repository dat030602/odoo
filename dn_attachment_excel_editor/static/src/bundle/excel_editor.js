/** @odoo-module */
import { Component, onWillStart, useExternalListener, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Spreadsheet, load } from "@odoo/o-spreadsheet";
import { useSpreadsheetNotificationStore } from "@spreadsheet/hooks";
import { OdooSpreadsheetModel } from "@spreadsheet/model";
import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";

const ACTION_TAG = "dn_attachment_excel_editor";
const XLSX_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

const ATTR_MIN_RE = /(\bmin\s*=\s*)(["'])(.*?)\2/i;
const ATTR_MAX_RE = /(\bmax\s*=\s*)(["'])(.*?)\2/i;
const CHART_F_TAG_RE = /<c:f>([^<]+)<\/c:f>/gi;
const CHART_RANGE_RE = /^(?:('?[^'!]+'?)!)?(\$?)([A-Za-z]+)(\$?)([0-9]+):(\$?)([A-Za-z]+)(\$?)([0-9]+)$/;

/**
 * Sanitize chart XML strings to prevent negative column/row indexing on import.
 * When series has a title reference, o-spreadsheet's convertExcelRangeToSheetXC
 * decrements zone.left (if height=1) or zone.top (if width=1) by 1.
 * Decrementing 0 to -1 throws 'Error: number must be positive. Got -1'.
 */
function sanitizeChartXml(xmlString) {
    if (
        typeof xmlString !== "string" ||
        !xmlString.includes("<c:chart") ||
        !/<c:tx\b[\s\S]*?<c:f\b/i.test(xmlString)
    ) {
        return xmlString;
    }
    return xmlString.replace(CHART_F_TAG_RE, (match, formula) => {
        const trimmed = formula.trim();
        const rm = trimmed.match(CHART_RANGE_RE);
        if (!rm) return match;

        const [, sheet, c1Fix, c1, r1Fix, r1Str, c2Fix, c2, r2Fix, r2Str] = rm;
        const prefix = sheet ? `${sheet}!` : "";
        const col1 = c1.toUpperCase();
        const col2 = c2.toUpperCase();
        const row1 = parseInt(r1Str, 10);
        const row2 = parseInt(r2Str, 10);

        if (row1 === row2 && col1 === "A") {
            return `<c:f>${prefix}${c1Fix}B${r1Fix}${row1}:${c2Fix}${c2}${r2Fix}${row2}</c:f>`;
        }
        if (col1 === col2 && row1 === 1) {
            return `<c:f>${prefix}${c1Fix}${col1}${r1Fix}2:${c2Fix}${c2}${r2Fix}${row2}</c:f>`;
        }
        return match;
    });
}

/**
 * Sanitize worksheet XML strings to ensure all <col> elements have valid min/max.
 * o-spreadsheet throws 'number must be positive. Got -1' in numberToLetters(colIndex - 1)
 * when col.min is 0 or negative. OpenXML standard requires 1-based column indexing.
 */
function sanitizeWorksheetXml(xmlString) {
    if (typeof xmlString !== "string" || !/<col\b/i.test(xmlString)) {
        return xmlString;
    }
    return xmlString.replace(/<col\b([^>]*)\/?>/gi, (tag) => {
        const minMatch = tag.match(ATTR_MIN_RE);
        const maxMatch = tag.match(ATTR_MAX_RE);
        if (!minMatch && !maxMatch) {
            return tag;
        }
        let minVal = minMatch ? parseInt(minMatch[3].trim(), 10) : null;
        let maxVal = maxMatch ? parseInt(maxMatch[3].trim(), 10) : null;
        if (minVal !== null && isNaN(minVal)) minVal = 1;
        if (maxVal !== null && isNaN(maxVal)) maxVal = 1;

        if (minVal !== null && minVal < 1) {
            minVal = 1;
        }
        if (maxVal !== null && maxVal < 1) {
            maxVal = minVal !== null ? minVal : 1;
        }
        if (minVal !== null && maxVal !== null && maxVal < minVal) {
            maxVal = minVal;
        }

        let result = tag;
        if (minMatch && minVal !== null) {
            result = result.replace(ATTR_MIN_RE, (m, p1, p2) => `${p1}${p2}${minVal}${p2}`);
        }
        if (maxMatch && maxVal !== null) {
            result = result.replace(ATTR_MAX_RE, (m, p1, p2) => `${p1}${p2}${maxVal}${p2}`);
        }
        return result;
    });
}

/** Normalize file list returned by model.exportXLSX() for server payload. */
function serializeFiles(files) {
    return files.map((f) => {
        if (f.imageSrc !== undefined) {
            return { path: f.path, imageSrc: f.imageSrc };
        }
        let content = f.content;
        if (typeof content === "string" && f.path.toLowerCase().endsWith(".xml")) {
            content = sanitizeWorksheetXml(content);
            content = sanitizeChartXml(content);
        }
        return { path: f.path, content };
    });
}

function base64ToBlob(b64, type) {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) {
        bytes[i] = bin.charCodeAt(i);
    }
    return new Blob([bytes], { type });
}

// ----------------------------------------------------------------------
// Save Options Dialog
// ----------------------------------------------------------------------
export class ExcelSaveDialog extends Component {
    static template = "dn_attachment_excel_editor.ExcelSaveDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        onConfirm: Function,
    };

    setup() {
        this.state = useState({
            saveMode: "overwrite",
            rememberChoice: false,
        });
    }

    async onConfirm() {
        await this.props.onConfirm({
            saveMode: this.state.saveMode,
            rememberChoice: this.state.rememberChoice,
        });
        this.props.close();
    }

    onCancel() {
        this.props.close();
    }
}

// ----------------------------------------------------------------------
// Spreadsheet Editor Component
// ----------------------------------------------------------------------
export class ExcelEditor extends Component {
    static template = "dn_attachment_excel_editor.ExcelEditor";
    static components = { Spreadsheet };
    static props = {
        attachmentId: { type: Number, optional: true },
        attachmentName: { type: String, optional: true },
        onClose: Function,
        onExpand: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        useSpreadsheetNotificationStore();

        this.model = null;
        this.writeDate = null;
        this.cleanRevisionId = null;
        this.state = useState({
            attachmentId: this.props.attachmentId,
            name: this.props.attachmentName || "",
            saveOption: "ask",
            dirty: false,
            saving: false,
            readonly: false,
            hasMacro: false,
            error: "",
        });

        useExternalListener(window, "keydown", this.onKeydown.bind(this), { capture: true });
        useExternalListener(window, "beforeunload", (ev) => {
            if (this.state.dirty) {
                ev.preventDefault();
                ev.returnValue = "";
            }
        });
        onWillStart(() => this.loadFile());
    }

    // ------------------------------------------------------------------
    // Load
    // ------------------------------------------------------------------
    async loadFile() {
        if (!this.state.attachmentId) {
            this.state.error = _t("Attachment details are missing. Please reopen the file from its record.");
            return;
        }
        let res;
        try {
            res = await this.orm.call("ir.attachment", "excel_editor_load", [
                [this.state.attachmentId],
            ]);
        } catch (error) {
            this.state.error = error?.data?.message || error?.message || String(error);
            return;
        }
        if (res && res.files) {
            for (const [path, content] of Object.entries(res.files)) {
                if (typeof content === "string" && path.toLowerCase().endsWith(".xml")) {
                    res.files[path] = sanitizeChartXml(sanitizeWorksheetXml(content));
                }
            }
        }
        let data;
        try {
            data = load(res.files, true);
        } catch (error) {
            console.error(error);
            this.state.error = _t("Could not parse Excel spreadsheet: %s", error.message);
            return;
        }
        this.state.name = res.name;
        this.state.hasMacro = res.has_macro;
        this.state.readonly = !res.can_write;
        this.state.saveOption = res.save_option || "ask";
        this.writeDate = res.write_date;
        this.model = new OdooSpreadsheetModel(
            data,
            {
                mode: res.can_write ? "normal" : "readonly",
                custom: { env: this.env, odooDataProvider: new OdooDataProvider(this.env) },
            },
            []
        );
        this.cleanRevisionId = this.model.session.getRevisionId();
        this.model.on("update", this, () => this.updateDirty());
        if (this.env.debug) {
            window.__excelEditorModel = this.model;
        }
    }

    updateDirty() {
        this.state.dirty = this.model.session.getRevisionId() !== this.cleanRevisionId;
    }

    get canSave() {
        return !!this.model && !this.state.readonly;
    }

    // ------------------------------------------------------------------
    // Save / Download
    // ------------------------------------------------------------------
    async promptSaveChoice() {
        return new Promise((resolve) => {
            this.dialog.add(ExcelSaveDialog, {
                onConfirm: (choice) => resolve(choice),
                close: () => resolve(null),
            });
        });
    }

    /** @returns {Promise<boolean>} true if saved successfully */
    async save() {
        if (!this.canSave || this.state.saving) {
            return false;
        }

        let saveMode = this.state.saveOption;
        let rememberChoice = false;

        if (saveMode === "ask") {
            const choice = await this.promptSaveChoice();
            if (!choice) {
                return false;
            }
            saveMode = choice.saveMode;
            rememberChoice = choice.rememberChoice;
        }

        this.state.saving = true;
        try {
            const { files } = this.model.exportXLSX();
            const res = await this.orm.call("ir.attachment", "excel_editor_save", [
                [this.state.attachmentId],
                serializeFiles(files),
                this.writeDate,
                saveMode,
                rememberChoice,
            ]);

            this.writeDate = res.write_date;
            this.state.name = res.name;
            this.cleanRevisionId = this.model.session.getRevisionId();
            this.state.dirty = false;
            this.state.hasMacro = false;

            if (rememberChoice) {
                this.state.saveOption = saveMode;
            }

            if (res.is_new) {
                this.state.attachmentId = res.id;
                this.notification.add(_t("Created new version: %s", res.name), { type: "success" });
            } else {
                this.notification.add(_t("Excel file saved successfully."), { type: "success" });
            }
            return true;
        } catch (error) {
            const msg = error?.data?.message || error?.message || String(error);
            this.notification.add(msg, { type: "danger" });
            return false;
        } finally {
            this.state.saving = false;
        }
    }

    async download() {
        if (!this.model) {
            return;
        }
        const { files } = this.model.exportXLSX();
        const res = await this.orm.call("ir.attachment", "excel_editor_export", [
            [this.state.attachmentId],
            serializeFiles(files),
        ]);
        const url = URL.createObjectURL(base64ToBlob(res.data, XLSX_MIMETYPE));
        const link = document.createElement("a");
        link.href = url;
        link.download = res.name;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 10000);
    }

    onKeydown(ev) {
        const key = ev.key ? ev.key.toLowerCase() : "";

        // Alt+S (or Ctrl+S / Cmd+S): Save
        if ((ev.altKey && key === "s") || ((ev.ctrlKey || ev.metaKey) && key === "s")) {
            ev.preventDefault();
            ev.stopPropagation();
            if (this.canSave && this.state.dirty) {
                this.save();
            }
            return;
        }

        // Esc: Close
        if (ev.key === "Escape") {
            ev.preventDefault();
            ev.stopPropagation();
            this.onClose();
            return;
        }
    }

    // ------------------------------------------------------------------
    // Close / expand
    // ------------------------------------------------------------------
    onClose() {
        if (!this.state.dirty || this.state.readonly) {
            return this.props.onClose();
        }
        this.dialog.add(ConfirmationDialog, {
            title: _t("Unsaved Changes"),
            body: _t("Do you want to save changes before closing?"),
            confirmLabel: _t("Save & Close"),
            cancelLabel: _t("Close without saving"),
            confirm: async () => {
                if (!(await this.save())) {
                    return false;
                }
                this.props.onClose();
            },
            cancel: () => this.props.onClose(),
            dismiss: () => {},
        });
    }

    onExpand() {
        if (!this.state.dirty || this.state.readonly) {
            return this.props.onExpand({
                id: this.state.attachmentId,
                name: this.state.name,
            });
        }
        this.dialog.add(ConfirmationDialog, {
            title: _t("Unsaved Changes"),
            body: _t("Changes must be saved before switching to full page view."),
            confirmLabel: _t("Save & Open Full Page"),
            cancelLabel: _t("Stay"),
            confirm: async () => {
                if (!(await this.save())) {
                    return false;
                }
                this.props.onExpand({
                    id: this.state.attachmentId,
                    name: this.state.name,
                });
            },
            cancel: () => {},
        });
    }
}

// ----------------------------------------------------------------------
// POPUP Mode: overlay added to main_components
// ----------------------------------------------------------------------
export class ExcelEditorPopup extends Component {
    static template = "dn_attachment_excel_editor.ExcelEditorPopup";
    static components = { ExcelEditor };
    static props = {
        attachmentId: { type: [Number, String], optional: true },
        attachmentName: { type: String, optional: true },
        onClose: Function,
        onExpand: Function,
    };
}

const POPUP_ID = "dn_attachment_excel_editor.popup";

registry.category(ACTION_TAG).add(
    "popup",
    {
        open(env, file) {
            const mainComponents = registry.category("main_components");
            const close = () => {
                if (mainComponents.contains(POPUP_ID)) {
                    mainComponents.remove(POPUP_ID);
                }
            };
            close();
            mainComponents.add(POPUP_ID, {
                Component: ExcelEditorPopup,
                props: {
                    attachmentId: Number(file.id),
                    attachmentName: file.name,
                    onClose: close,
                    onExpand: (currentFile) => {
                        close();
                        const target = currentFile || file;
                        env.services.action.doAction({
                            type: "ir.actions.client",
                            tag: ACTION_TAG,
                            name: target.name,
                            params: { attachment_id: target.id, attachment_name: target.name },
                        });
                    },
                },
            });
        },
    },
    { force: true }
);

// ----------------------------------------------------------------------
// FULL PAGE Mode: client action replacing backend lazy loader
// ----------------------------------------------------------------------
export class ExcelEditorAction extends Component {
    static template = "dn_attachment_excel_editor.ExcelEditorAction";
    static components = { ExcelEditor };
    static props = { "*": true };

    setup() {
        this.action = useService("action");
    }

    get params() {
        return this.props.action?.params || this.props.action?.context || {};
    }

    get attachmentId() {
        return this.params.attachment_id || this.props.attachment_id;
    }

    get attachmentName() {
        return this.params.attachment_name || this.props.attachment_name;
    }

    onClose() {
        this.action.restore().catch(() => browser.history.back());
    }
}

registry.category("actions").add(ACTION_TAG, ExcelEditorAction, { force: true });
