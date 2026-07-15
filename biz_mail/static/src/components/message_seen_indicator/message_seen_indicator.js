/** @odoo-module **/

import { MessageSeenIndicator } from '@mail/components/message_seen_indicator/message_seen_indicator';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { patch } from 'web.utils';
import Popover from "web.Popover";

const components = { MessageSeenIndicator, Popover };

patch(components.MessageSeenIndicator.prototype, 'message_seen_indicator', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    
    setup() {
        this._super();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'actionRef', refName: 'action' });
    },
    /**
     * @private
     */
    // showPopover(ev) {
    //     ev.stopPropagation();
    //     $('.biz_show_more').trigger('click');
    //     console.log('aaaaaaaa123123')
    // }

});
