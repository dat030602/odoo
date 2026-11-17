/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { addSpreadsheetActionLazyLoader } from "@spreadsheet/assets_backend/spreadsheet_action_loader";

export const EXCEL_ACTION_TAG = "dn_attachment_excel_editor";
const EXCEL_EXTENSIONS = ["xlsx", "xlsm"];
const EXCEL_MIMETYPES = [
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel.sheet.macroEnabled.12",
];

// Full-page client action lazy loader: spreadsheet bundle is loaded only when needed.
addSpreadsheetActionLazyLoader(EXCEL_ACTION_TAG);

export function isExcelFile(file) {
    const ext = (file.name || "").split(".").pop().toLowerCase();
    return EXCEL_EXTENSIONS.includes(ext) || EXCEL_MIMETYPES.includes(file.mimetype);
}

/**
 * Open Excel attachment in popup or full page mode.
 * @param {object} env
 * @param {{id: number, name: string}} file
 * @param {"popup"|"page"} mode
 */
export async function openExcelAttachment(env, file, mode = "popup") {
    if (mode === "page") {
        return env.services.action.doAction({
            type: "ir.actions.client",
            tag: EXCEL_ACTION_TAG,
            name: file.name,
            params: { attachment_id: file.id, attachment_name: file.name },
        });
    }
    try {
        await loadBundle("spreadsheet.o_spreadsheet");
    } catch (error) {
        env.services.notification.add(_t("Could not load spreadsheet editor."), {
            type: "danger",
        });
        throw error;
    }
    registry.category(EXCEL_ACTION_TAG).get("popup").open(env, file);
}
