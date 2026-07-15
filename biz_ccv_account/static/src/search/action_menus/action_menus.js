/** @odoo-module **/

import { ActionMenus } from "@web/search/action_menus/action_menus";
import { useService } from "@web/core/utils/hooks";
import { patch } from 'web.utils';

import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";


patch(ActionMenus.prototype, "customActionMenus" , {
    setup(){
        this._super.apply();
        this.user = useService("user");
        this.hideFields = useState({ check: false });
        onWillStart(async () => {
            this.showResPartner = this.props.resModel === "res.partner" && (await this.user.hasGroup("biz_ccv_account.group_delete_customer_supplier"));
            this.showHrEmployee = this.props.resModel === "hr.employee" && (await this.user.hasGroup("biz_ccv_account.group_delete_employee"));
            await this.isHideFields();
        });

    },

    async isHideFields(){
        if (this.props.resModel === "res.partner"){
            let activeIds = this.props.getActiveIds();
            
            if (activeIds.length != 0){
                var hideFields = await this.orm.silent.call("res.partner", "get_hide_fields", [activeIds]);
                this.hideFields.check = hideFields
            }
            
        }
    },

    //---------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------

    async setActionItems(props) {
        const result = await this._super(...arguments);
        var newResult = [];
        var _this = this;

        const setModels = new Set(["res.partner", "hr.employee"]);

        if (setModels.has(props.resModel)){

            if(this.showHrEmployee == undefined || this.showHrEmployee == "undefined"){
                await this.user.hasGroup("biz_ccv_account.group_delete_employee").then(function(userHasGroup) {
                    _this.showHrEmployee = userHasGroup;
                })
            }

            if(!_this.showResPartner && props.resModel === "res.partner"){
                //Need fix
                for(var i=0; i<result.length; i++){
                    if(result[i].key != "delete" && result[i].description != "Merge" && result[i].description != "Hợp nhất"){
                        newResult.push(result[i])
                    }
                }
            }else if(!_this.showHrEmployee && props.resModel === "hr.employee"){
                for(var i=0; i<result.length; i++){
                    if(result[i].key != "delete"){
                        newResult.push(result[i])
                    }
                }
            }
            if(newResult.length != 0 ) return newResult;
        }
        return result;
    }
})