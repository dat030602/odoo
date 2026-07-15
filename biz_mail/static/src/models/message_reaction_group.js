/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';
import { sprintf } from '@web/core/utils/strings';


registerPatch({
    name: 'MessageReactionGroup',
    recordMethods: {

        //Fixme: If you move the mouse quickly over the icons, an error appears
        showUsersReaction(ev){
           
            if(this.message && this.content){
                if (!this.reactionPopoverView) {
                    this.update({ reactionPopoverView: {} });
                } 
            }
        },

        unShowUsersReaction(ev){
            const member_count = this.partners.length
            if (this.reactionPopoverView && member_count <= 10) {
                this.update({ reactionPopoverView: clear() });
            } 
        },

        _onClickShowMore(ev) {
            this.update({ hasShowMoreButton: true});
        },

        _onClickShowLess(ev) {
            this.update({ hasShowMoreButton: false});
        },
        
    },
    fields: {
        actionRef: attr(),
        reactionPopoverView: one('PopoverView', {
            inverse: 'messageReactionGroupOwnerAsReaction',
        }),

        classNames: attr({
            compute() {
                const classNames = [];
                classNames.push(this.paddingClassNames);
                classNames.push('fa fa-lg fa-smile-o o_MessageActionView_actionReaction');
                return classNames.join(' ');
            },
            default: '',
        }),

        summary: {
            compute() {
                return sprintf(this.env._t('See who reacted with emoticon %s and react the same'), this.content);
            }
        },

        hasShowMoreButton: attr({
            default: false,
        }),
    },
});
