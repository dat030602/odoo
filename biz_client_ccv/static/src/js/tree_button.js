/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from "@web/core/utils/hooks";

export class AccountMoveListController extends ListController {
   setup() {
      this.rpc = useService('rpc');
      super.setup();
   }
   async CreateInvoice() {
      const viewId = await this.rpc('/get_id_create_invoice_wizard')
      var move_type = false
      if (this.props.context.default_move_type == 'out_invoice') {
         move_type = 'out_invoice'
      }
      if (this.props.context.default_move_type == 'in_invoice') {
         move_type = 'in_invoice'
      }
       this.actionService.doAction({
          type: 'ir.actions.act_window',
          res_model: 'create.invoice.wizard',
          name:'Create Invoice',
          view_mode: 'form',
          view_type: 'form',
          views: [[viewId, 'form']],
          target: 'new',
          res_id: false,
          context: {'move_type': move_type}
      });
   }
}
registry.category("views").add("button_create_invoice", {
   ...listView,
   Controller: AccountMoveListController,
   buttonTemplate: "biz_client_ccv.ListView.Buttons",
});