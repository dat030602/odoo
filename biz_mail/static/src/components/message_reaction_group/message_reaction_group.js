/** @odoo-module **/

import { MessageReactionGroup } from '@mail/components/message_reaction_group/message_reaction_group';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { patch } from 'web.utils';

const components = { MessageReactionGroup };

patch(components.MessageReactionGroup.prototype, 'message_reaction_group', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    setup() {
        this._super();
        // this._groupMessagesSearchInputRef = useRef('groupMessagesSearchInput')
        useRefToModel({ fieldName: 'actionRef', refName: 'action' });
        // useRefToModel({ fieldName: 'groupMessagesSearchInput', refName: 'groupMessagesSearchInput' });
    },

});
