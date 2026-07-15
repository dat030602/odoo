/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';

const { Component } = owl;

export class EmojiPickerMessageReactionView extends Component {
    setup() {
        useComponentToModel({ fieldName: 'component' });
    }
    /**
     * @returns {EmojiPickerMessageReactionView}
     */
    get emojiPickerMessageReactionView() {
        return this.props.record;
    }
}

Object.assign(EmojiPickerMessageReactionView, {
    props: { record: Object },
    template: 'biz_mail.EmojiPickerMessageReactionView',
});

registerMessagingComponent(EmojiPickerMessageReactionView);
