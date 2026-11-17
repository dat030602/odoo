import { AttachmentList } from "@mail/core/common/attachment_list";
import { Attachment } from "@mail/core/common/attachment_model";
import { isExcelFile, openExcelAttachment } from "./excel_opener";
import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    get isViewable() {
        return super.isViewable || isExcelFile(this);
    },
});

patch(AttachmentList.prototype, {
    onClickAttachment(attachment) {
        if (isExcelFile(attachment)) {
            openExcelAttachment(this.env, { id: attachment.id, name: attachment.name }, "popup");
            return;
        }
        super.onClickAttachment(attachment);
    },
});
