/** @odoo-module **/

import { ModelField } from '@mail/model/model_field';
import { patch } from 'web.utils';


patch(ModelField.prototype, "customModelField" , {
    read(record) {
        try {
            return record.__values.get(this.fieldName);
        } catch(e) {
            console.log("error", e)
        }
    },
})