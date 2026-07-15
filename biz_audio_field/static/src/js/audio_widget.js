/** @odoo-module */

import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { CharField } from "@web/views/fields/char/char_field";
import {BinaryField} from '@web/views/fields/binary/binary_field';
import {isBinarySize} from '@web/core/utils/binary';
import {url} from '@web/core/utils/urls';

export class BinaryFieldAudio extends BinaryField {

    setup() {
        super.setup();
    }

    get url() {
        if (isBinarySize(this.props.value)) {
            return url('/web/content', {
                model: this.props.record.resModel,
                id: this.props.record.resId,
                field: this.props.name,
            })
        }
    }

}

BinaryFieldAudio.template = 'biz_audio_field.BinaryFieldAudio';
BinaryFieldAudio.defaultProps = {
    ...BinaryField.defaultProps,
    acceptedFileExtensions: 'audio/wav',
};

registry.category('fields').add('binary_audio', BinaryFieldAudio);