/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { listView } from '@web/views/list/list_view';
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

/**
 * List view for the <sale.order> model.
 *
 * Add an import button to open the wizard <sale.order.import>. This wizard
 * allows the user to import sale order
 */
export class SaleOrderImPort extends ListController {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    export_stock_quant() {
       this.actionService.doAction({
           type: 'ir.actions.act_window',
           res_model: 'alpha.report',
           name :'Biên bản kiểm kê vật tư hàng hóa',
           view_mode: 'form',
           view_type: 'form',
           views: [[false, 'form']],
           target: 'current',
           res_id: false,
           context: {
              'default_is_wizard': true,
              'default_type': false,
           }
       });
    }
};

registry.category('views').add('button_export_stock_quant', {
    ...listView,
    Controller: SaleOrderImPort,
    buttonTemplate: 'ccv_sql.export_stock_quant',
});