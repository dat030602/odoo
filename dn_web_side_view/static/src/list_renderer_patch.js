/** @odoo-module */

import { ListRenderer } from '@web/views/list/list_renderer';
import { patch } from '@web/core/utils/patch';

patch(ListRenderer.prototype, {

    async handleFormX2ManyRelationalCellClick(record, ev, mode) {
        if (!record?.resId || mode === "default") {
            return false;
        }

        if (mode === "split") {
            return this.action_form_split_cellClicked(this.env, record, null, ev, this.env.mjbFormActions);
        }

        ev.preventDefault();
        ev.stopPropagation();

        await this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: record.resModel,
            res_id: record.resId,
            views: [[false, "form"]],
            target: mode === "popup" ? "new" : "current",
            context: record.context || {},
        });
        return true;
    },

    async action_popup_cellClicked(env, record, column, ev, action) {
        await this.env.services.action.doAction({
            type: "ir.actions.act_window",
            target: "new",
            res_model: record.resModel,
            res_id: record.resId,
            views: [[false, "form"]],
            context: record.context || {},
        });
    },

    async action_split_cellClicked(env, record, column, ev, action) {
        action.setSelectedRecordId(record.resId);
        const tbody = ev.target.closest('tbody');
        if (tbody) {
            tbody.querySelectorAll('tr').forEach(tr => tr.classList.remove('table-info'));
            const currentRow = ev.target.closest('tr');
            if (currentRow) {
                currentRow.classList.add('table-info');
            }
        }
    },

    async action_form_split_cellClicked(env, record, column, ev, action) {
        action.setSelectedRecord(record.resId, record.resModel);
        return true;
    },

    async action_form_current_cellClicked(env, record, column, ev, action) {
        await this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: record.resModel,
            res_id: record.resId,
            views: [[false, "form"]],
            target: "current",
            context: record.context || {},
        });
    },
    
    async onCellClicked(record, column, ev) {
        const env = this.env;
        const config = env.config;
        const isFormView = config?.viewType === "form";
        const action = isFormView ? env.mjbFormActions : env.mjbListActions;
        const mode = action?.mode || "default";
        const fieldType = record?.fields?.[column?.name]?.type;
        const x2ManyConfig = env.mjbX2ManyConfig;

        // Only handle x2many list flow in form view for readonly/editable=0.
        if (isFormView) {
            if (!x2ManyConfig?.enabled) {
                return super.onCellClicked(...arguments);
            }

            const isReadonlyOrNonEditable = !this.props.editable || this.props.readonly;
            if (!isReadonlyOrNonEditable) {
                return super.onCellClicked(...arguments);
            }

            // Widget/custom HTML can define their own clickable flow; keep core behavior.
            const hasInteractiveTarget = !!ev.target.closest(
                "a,button,input,textarea,select,label,[role='button']"
            );
            if (hasInteractiveTarget) {
                return super.onCellClicked(...arguments);
            }

            if (column?.type === "field" && fieldType !== "many2one") {
                if (mode === "split") {
                    return this.action_form_split_cellClicked(env, record, column, ev, action);
                }
                if (mode === "current") {
                    return this.action_form_current_cellClicked(env, record, column, ev, action);
                }
                const handled = await this.handleFormX2ManyRelationalCellClick(record, ev, mode);
                if (handled) {
                    return;
                }
            }

            return super.onCellClicked(...arguments);
        }

        if (mode === "popup") {
            await this.action_popup_cellClicked(env, record, column, ev, action);
            return;
        }
        else if (mode === "split") {
            await this.action_split_cellClicked(env, record, column, ev, action);
            return;
        }

        super.onCellClicked(...arguments);
    },
});
