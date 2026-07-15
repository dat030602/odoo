/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from '@web/core/utils/hooks';
const PreviewDialog = require("biz_viettel_sinvoice_v2.PreviewDialog");
var rpc = require('web.rpc');

export class PreviewPDFInvoice extends Component {
    setup() {
        this.root = this.env.root
        this.type = this.props.type
        this.notificationService = useService('notification');
        this.recordData  = this.props.record.data
    }
    async onPreview() {
        var self = this;
        var a = await this.props.record.save();
        if (!a){
            return
        }
        var this_id = this.recordData.id;
        return rpc.query({
            model: 'viettel.sinvoice',
            method: 'action_get_preview_pdf',
            args: [this_id]
        }).then(function (result) {
            if (result.success && result.attachment){
                var url = '/web/content/' + result.attachment
                var title = 'Preview';
                PreviewDialog.createPreviewDialog(self, url, title);
            }else{
                alert(result.error || "Có lỗi xảy ra")
            }
        });
    }
    
}

PreviewPDFInvoice.template = "biz_viettel_sinvoice_v2.PreviewPdfWidget";
PreviewPDFInvoice.extractProps = ({ attrs }) => ({
    type: attrs.type || "",
});
PreviewPDFInvoice.props = {
    record: { type: Object, optional: true},
    type: { type: String, optional: true },
    readonly: { type: Boolean, optional: 1 },
}
registry.category("view_widgets").add("preview_einv_pdf", PreviewPDFInvoice);
