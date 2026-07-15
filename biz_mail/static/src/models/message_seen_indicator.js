/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

// khong sai
registerPatch({
    name: 'MessageSeenIndicator',
    fields: {
        actionRef: attr(),
    },
});
