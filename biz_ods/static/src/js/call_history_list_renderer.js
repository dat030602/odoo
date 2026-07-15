/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";

const { onMounted, useExternalListener, onPatched, onWillUnmount } = owl;

export class CallHistoryListRenderer extends ListRenderer {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            console.log('custom onMounted')
            const audio = document.getElementsByClassName("audioCCV");
            for (let i = 0; i < audio.length; i++) {
                audio[i].addEventListener("loadedmetadata", scriptAudioCCV);
            }
        })
        onPatched(() => {
            console.log('custom onPatched')
            const audio = document.getElementsByClassName("audioCCV");
            for (let i = 0; i < audio.length; i++) {
                audio[i].addEventListener("loadedmetadata", scriptAudioCCV);
            }
        })
        onWillUnmount(() => {
            console.log('custom onWillUnmount')
            const audio = document.getElementsByClassName("audioCCV");
            for (let i = 0; i < audio.length; i++) {
                audio[i].removeEventListener("loadedmetadata", scriptAudioCCV);
            }
        })
    }
}

registry.category("views").add('biz_ods_call_history_tree', {
    ...listView,
    Renderer: CallHistoryListRenderer
});