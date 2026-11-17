/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";
import { isExcelFile, openExcelAttachment } from "./excel_opener";

patch(Many2ManyBinaryField.prototype, {
    isExcel(file) {
        return isExcelFile(file);
    },

    /**
     * Handle attachment click: if it's an Excel file, open in spreadsheet editor;
     * otherwise retain default Odoo behavior (download file).
     */
    onClickAttachment(ev, file) {
        if (!this.isExcel(file)) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        openExcelAttachment(this.env, { id: file.id, name: file.name }, "popup");
    },
});
