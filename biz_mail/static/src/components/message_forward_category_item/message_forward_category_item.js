/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update';
const { Component, useRef } = owl;


export class MessageForwardCategoryItem extends Component {

    /**
     * @returns {MessageForwardCategoryItem}
     */
    get categoryItem() {
        return this.props.record;
    }

}

Object.assign(MessageForwardCategoryItem, {
    props: { record: Object },
    template: 'biz_mail.MessageForwardCategoryItem',
});

registerMessagingComponent(MessageForwardCategoryItem);
