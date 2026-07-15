/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';

const { Component } = owl;

export class EmojiPickerMessageSeenIndicatorView extends Component {
    setup() {
        useComponentToModel({ fieldName: 'component' });
    }
    /**
     * @returns {EmojiPickerMessageSeenIndicatorView}
     */
    get emojiPickerMessageSeenIndicatorView() {
        return this.props.record;
    }
}

Object.assign(EmojiPickerMessageSeenIndicatorView, {
    props: { record: Object },
    template: 'biz_mail.EmojiPickerMessageSeenIndicatorView',
});

registerMessagingComponent(EmojiPickerMessageSeenIndicatorView);
