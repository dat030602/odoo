/** @odoo-module */

import { registry } from "@web/core/registry";
import { formView } from '@web/views/form/form_view';
import { FormRenderer } from '@web/views/form/form_renderer';

const { onMounted, useExternalListener, onWillUnmount } = owl;

export class CallHistoryFormRenderer extends FormRenderer {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            const audio = document.getElementsByClassName("audioCCV");
            for (let i = 0; i < audio.length; i++) {
                audio[i].addEventListener("loadedmetadata", scriptAudioCCV);
            }
        })
        onWillUnmount(() => {
            const audio = document.getElementsByClassName("audioCCV");
            for (let i = 0; i < audio.length; i++) {
                audio[i].removeEventListener("loadedmetadata", scriptAudioCCV);
            }
        })
    }
}

registry.category("views").add('biz_ods_call_history_form', {
    ...formView,
    Renderer: CallHistoryFormRenderer
});