import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { Component, xml, onWillStart, toRaw, useSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { View } from "@web/views/view";
import { DynamicList } from "@web/model/relational_model/dynamic_list";
import { Record as RelationalRecord } from "@web/model/relational_model/record";

// --- PATCH ĐỂ XỬ LÝ EVALCONTEXT LOCAL ---
// Tránh đưa 'parent' vào View context vì nó sẽ gửi lên backend gây sập server (ERR_CONNECTION_RESET).
const originalListSetup = DynamicList.prototype.setup;
DynamicList.prototype.setup = function () {
    originalListSetup.apply(this, arguments);
    if (this.model && this.model.env && this.model.env.x2manyFullscreenParentData) {
        this.evalContext = Object.assign({}, this.context, {
            parent: this.model.env.x2manyFullscreenParentData
        });
    }
};

const originalRecordSetEvalContext = RelationalRecord.prototype._setEvalContext;
RelationalRecord.prototype._setEvalContext = function () {
    originalRecordSetEvalContext.apply(this, arguments);
    if (!this._parentRecord && this.model && this.model.env && this.model.env.x2manyFullscreenParentData) {
        this.evalContext.parent = this.model.env.x2manyFullscreenParentData;
        this.evalContextWithVirtualIds.parent = this.model.env.x2manyFullscreenParentData;
    }
};
// ---------------------------------------

// 1. Component Client Action để render View động từ X2Many
class X2ManyFullscreenAction extends Component {
    static template = xml`<View t-if="isReady" t-props="viewProps" />`;
    static components = { View };
    setup() {
        const params = this.props.action.params;
        this.viewService = useService("view");
        this.isReady = false;
        
        // Đưa parent data vào Env để ListRenderer/Record dùng nội bộ
        useSubEnv({ x2manyFullscreenParentData: params.parentData || {} });

        this.viewProps = {
            type: "list",
            resModel: params.resModel,
            arch: params.arch,
            fields: params.fields,
            domain: params.domain,
            context: this.props.action.context || {}, // Khôi phục lại context gốc, không chứa parent!
            display: { controlPanel: true }, 
            loadActionMenus: true, 
            loadIrFilters: true, 
            searchViewId: false, 
        };

        onWillStart(async () => {
            let relatedModels = { [params.resModel]: { fields: params.fields } };
            
            if (params.parentResModel) {
                try {
                    const parentViews = await this.viewService.loadViews({
                        resModel: params.parentResModel,
                        views: [[params.parentViewId, "form"]],
                        context: this.props.action.context || {},
                    });
                    relatedModels = {
                        ...parentViews.relatedModels,
                        ...relatedModels
                    };
                } catch (e) {
                    console.warn("Could not load parent view models", e);
                }
            }
            
            this.viewProps.relatedModels = relatedModels;
            this.isReady = true;
        });
    }
}
registry.category("actions").add("dn_x2many_fullscreen_action", X2ManyFullscreenAction);

// 2. Gắn sự kiện cho nút Mở rộng ở X2Many
patch(X2ManyField.prototype, {
    async openFullscreenAction() {
        // Lưu Form hiện tại trước khi chuyển trang
        await this.props.record.save();
        
        const currentIds = this.list.currentIds.filter((id) => typeof id === "number");

        // Lấy kiến trúc View inline
        let arch = "<list><field name='display_name'/></list>";
        if (this.archInfo && this.archInfo.xmlDoc) {
            arch = this.archInfo.xmlDoc.outerHTML;
        } else if (this.activeField && this.activeField.views && this.activeField.views.list) {
            arch = this.activeField.views.list.arch;
        }

        const parentViewId = (this.env.config && this.env.config.views && this.env.config.views.find(v => v[1] === "form")) ? this.env.config.views.find(v => v[1] === "form")[0] : false;

        let parentData = {};
        if (this.props.record && this.props.record.data) {
            const rawData = toRaw(this.props.record.data);
            for (const key in rawData) {
                if (typeof rawData[key] !== "object" && typeof rawData[key] !== "function") {
                    parentData[key] = rawData[key];
                }
            }
        }

        // Gọi action
        this.action.doAction({
            type: "ir.actions.client",
            tag: "dn_x2many_fullscreen_action",
            name: this.props.string || "Chi tiết",
            params: {
                resModel: this.list.resModel,
                parentResModel: this.props.record.resModel,
                parentViewId: parentViewId,
                arch: arch,
                fields: this.props.relatedFields, 
                domain: [["id", "in", currentIds]],
                parentData: parentData,
            },
            context: this.props.context,
            target: "current", 
        });
    }
});
