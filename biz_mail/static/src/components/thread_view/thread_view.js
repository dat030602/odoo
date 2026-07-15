/** @odoo-module **/

import { ThreadView } from '@mail/components/thread_view/thread_view';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { patch } from 'web.utils';

const components = { ThreadView };

patch(components.ThreadView.prototype, 'thread_view', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    setup() {
        this._super();
        // this._groupMessagesSearchInputRef = useRef('groupMessagesSearchInput')
        useRefToModel({ fieldName: 'messageSearchInput', refName: 'messageSearchInput' });
    },

});
