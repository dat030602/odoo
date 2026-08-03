/** @odoo-module */

import { X2ManyField } from '@web/views/fields/x2many/x2many_field';
import { patch } from '@web/core/utils/patch';
import { useSubEnv } from '@odoo/owl';

patch(X2ManyField.prototype, {
    setup() {
        super.setup(...arguments);

        useSubEnv({
            mjbX2ManyConfig: {
                enabled: true,
                sourceField: this.props.name,
            },
        });
    },
});
