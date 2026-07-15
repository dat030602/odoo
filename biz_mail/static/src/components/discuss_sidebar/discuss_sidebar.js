/** @odoo-module **/

import { DiscussSidebar } from '@mail/components/discuss_sidebar/discuss_sidebar';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { patch } from 'web.utils';

const components = { DiscussSidebar };

patch(components.DiscussSidebar.prototype, 'discuss_sidebar', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    setup() {
        this._super();
        // this._groupMessagesSearchInputRef = useRef('groupMessagesSearchInput')
        useRefToModel({ fieldName: 'groupMessagesSearchInput', refName: 'groupMessagesSearchInput' });
    },

});
