/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

// khong sai
registerPatch({
    name: 'Partner',
    recordMethods: {
        convertData(data) {
            const data2 = {};
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('name' in data) {
                data2.name = data.name;
            }
            return data2;
        },
    },
});
