/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { markEventHandled } from '@mail/utils/utils';
registerPatch({
    name: 'MessageActionView',
    recordMethods:{
        // action click forward
        // onClick(ev) {
        //     this._super()
        //     var check_show_forward = false
        //     switch (this.messageAction.messageActionListOwner) {
        //         case this.messageAction.messageActionListOwnerAsForward:
        //             this.update({ forwardConfirmDialog: {} });
        //             check_show_forward = true
        //             break
        //     }
            
        //     if (check_show_forward){
        //         this._clickForwardAction()
        //     }
            
        // },
        // no inherit
        onClick(ev) {
            switch (this.messageAction.messageActionListOwner) {
                case this.messageAction.messageActionListOwnerAsDelete:
                    this.update({ deleteConfirmDialog: {} });
                    break;
                case this.messageAction.messageActionListOwnerAsForward:
                    this.update({ forwardConfirmDialog: {} });
                    this._clickForwardAction()
                    break
                case this.messageAction.messageActionListOwnerAsEdit:
                    this.messageAction.messageActionListOwner.messageView.startEditing();
                    break;
                case this.messageAction.messageActionListOwnerAsMarkAsRead:
                    this.messageAction.messageActionListOwner.message.markAsRead();
                    break;
                case this.messageAction.messageActionListOwnerAsReaction:
                    if (!this.reactionPopoverView) {
                        this.update({ reactionPopoverView: {} });
                    } else {
                        this.update({ reactionPopoverView: clear() });
                    }
                    break;
                case this.messageAction.messageActionListOwnerAsReplyTo:
                    markEventHandled(ev, 'MessageActionList.replyTo');
                    this.messageAction.messageActionListOwner.messageView.replyTo();
                    break;
                case this.messageAction.messageActionListOwnerAsToggleCompact:
                    this.messageAction.messageActionListOwner.update({ isCompact: !this.messageAction.messageActionListOwner.isCompact });
                    break;
                case this.messageAction.messageActionListOwnerAsToggleStar:
                    this.messageAction.messageActionListOwner.message.toggleStar();
                    break;
            }
        },
        
        _clickForwardAction(ev){
            if (this.forwardConfirmDialog && this.forwardConfirmDialog.forwardMessageConfirmView && this.forwardConfirmDialog.forwardMessageConfirmView.messageView){
                this.forwardConfirmDialog.forwardMessageConfirmView.messageView.searchPartnersToForward()
                
            }
            else{
                console.log('Dialog không tìm thấy!!!!!')
            }
        }

    },
    fields: {
        // inherit
        classNames: {
            compute() {
                const classNames = [];
                var check = false
                classNames.push(this.paddingClassNames);
                switch (this.messageAction.messageActionListOwner) {
                    case this.messageAction.messageActionListOwnerAsForward:
                        check = true
                        classNames.push('fa fa-lg fa-mail-forward o_MessageActionView_actionForward');
                        break;
                }
                if(check){
                    return classNames.join(' ');
                }
                
                return this._super()
            },
        },
        // messageActionViewOwnerAsForwardConfirm.messageAction.messageActionListOwner.message
        forwardConfirmDialog: one('Dialog', {
            inverse: 'messageActionViewOwnerAsForwardConfirm',
        }),

        title: {
            compute(){
                switch (this.messageAction.messageActionListOwner) {
                    case this.messageAction.messageActionListOwnerAsForward:
                        return this.env._t("Forward");
                }
                return this._super()

            }
        }
    },
});
