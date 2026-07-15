/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MessagingMenu } from "@mail/components/messaging_menu/messaging_menu";
import { useService } from "@web/core/utils/hooks";

const { onWillStart } = owl;


patch(MessagingMenu.prototype, "custom_messaging_menu", {

    setup() {
        this._super.apply(this, arguments);
        this.user = useService("user");
        onWillStart(async () => {
            this.isHiddenChatUser = await this.user.hasGroup('biz_mail.group_hidden_menu_chat');
        });
    },

    get hiddenChat() {
        return this.isHiddenChatUser;
    }

});