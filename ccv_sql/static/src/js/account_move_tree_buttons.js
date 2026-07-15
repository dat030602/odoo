/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";

patch(ListController.prototype, "ccv_sql.ChildMoveButtons", {
    setup() {
        this._super(...arguments);
    },
    async createChildMoveDebit() {
        this.actionService.doAction('ccv_sql.action_create_debit_move');
    },
    async createChildMoveCredit() {
        this.actionService.doAction('ccv_sql.action_create_credit_move');
    }
});
