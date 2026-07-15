/** @odoo-module **/

import { PopoverView } from '@mail/components/popover_view/popover_view';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { patch } from 'web.utils';
import { usePosition } from '@web/core/position_hook';

const components = { PopoverView };

patch(components.PopoverView.prototype, 'popover_view', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    setup() {
        this._super();
        // this._groupMessagesSearchInputRef = useRef('groupMessagesSearchInput')
        // usePosition(
        //     () => this.popoverView.anchorRef && this.popoverView.anchorRef.el,
        //     {
        //         popper: "root",
        //         margin: 16,
        //         position: this.popoverView.position,
        //     }
        // );
    },

});
