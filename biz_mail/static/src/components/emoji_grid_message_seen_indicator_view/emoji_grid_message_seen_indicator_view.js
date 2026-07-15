/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';

const { Component } = owl;

export class EmojiGridMessageSeenIndicatorView extends Component {
    setup() {
        useRefToModel({ fieldName: 'containerRef', refName: 'containerRef'});
        useRefToModel({ fieldName: 'listRef', refName: 'listRef'});
        useRefToModel({ fieldName: 'viewBlockRef', refName: 'viewBlockRef'});
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    /**
     * @returns {EmojiGridMessageSeenIndicatorView}
     */
    get emojiGridMessageSeenIndicatorView() {
        return this.props.record;
    }
}

Object.assign(EmojiGridMessageSeenIndicatorView, {
    props: { record: Object },
    template: 'biz_mail.EmojiGridMessageSeenIndicatorView',
});

registerMessagingComponent(EmojiGridMessageSeenIndicatorView);
