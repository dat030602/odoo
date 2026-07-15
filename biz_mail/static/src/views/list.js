/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";

export class CustomListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async onClickSyncPartner(){
        const model = this.model.rootParams.resModel;
        await this.orm.call(model, "action_sync_partner", [], {});
        browser.location.reload();

//        await this.model.root.load();
//        this.render(true);

    }

    async onClickAddAllChannel() {
        const model = this.model.rootParams.resModel;
        await this.orm.call(model, "action_add_all_channel", [], {});
        browser.location.reload();

//        await this.model.root.load();
//        this.render(true);
    }
}

registry.category("views").add("all_channel_view_tree", {
    ...listView,
    Controller: CustomListController,
    buttonTemplate: "biz_mail.ListView.buttons",
});
