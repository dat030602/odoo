/** @odoo-module **/

import { Chatter } from "@mail/components/chatter/chatter";
import { patch } from 'web.utils';
import { useService } from "@web/core/utils/hooks";

import { onWillStart, useState } from "@odoo/owl";

patch(Chatter.prototype, "customChatter" , {
    setup() {
        this._super.apply();
        this.hideFields = useState({ check: false });
        this.orm = useService("orm");
        onWillStart(async () => {
            await this.isHideFields();
        });
    },

    async isHideFields(){
        if(this.props.record.threadModel === "res.partner") {
            var hideFields = await this.orm.silent.call("res.partner", "get_hide_fields", [this.props.record.threadId]);
            this.hideFields.check = hideFields
        }
    }
})