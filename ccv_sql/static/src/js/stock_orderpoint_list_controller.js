/** @odoo-module */

import { StockOrderpointListController } from "@stock/views/stock_orderpoint_list_controller";
import { patch } from "@web/core/utils/patch";

patch(StockOrderpointListController.prototype, "ccv_sql.StockOrderpointListController", {
    async onClickRecommendPackaging() {
        const resIds = await this.getSelectedResIds();
        if (resIds.length > 0) {
            const action = await this.model.orm.call(this.props.resModel, 'action_recommend_packaging', [resIds], {
                context: this.props.context,
            });
            if (action) {
                this.actionService.doAction(action);
            }
        }
    }
});
