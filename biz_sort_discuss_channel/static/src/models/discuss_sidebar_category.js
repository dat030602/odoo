/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'DiscussSidebarCategory',
    fields: {
        // Inherit
        categoryItemsOrderedByName: {
            sort() {
                return [
                    ['truthy-first', 'thread'],
                    ['truthy-first', 'thread.lastInterestDateTime'],
                    ['most-recent-first', 'thread.lastInterestDateTime'],
                    ['greater-first', 'channel.id'],
                ]
            }
        },
    },
});
