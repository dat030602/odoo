/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'MessageSeenIndicatorView',
    recordMethods: {
        showPopoverSeenMessage(ev){
            // if (!this.reactionPopoverView) {
            //     this.update({ reactionPopoverView: {} });
            // } else {
            //     this.update({ reactionPopoverView: clear() });
            // }
            console.log("showPopoverSeenMessage---------->>>" + this.reactionPopoverView)
            this.update({ reactionPopoverView: this.reactionPopoverView ? clear() : {} });
        },
    },
    fields: {
        actionRef: attr(),
        reactionPopoverView: one('PopoverView', {
            inverse: 'messageSeenIndicatorViewOwnerAsReaction',
        }),

        component: attr(),

        // classNames: attr({
        //     compute() {
        //         const classNames = [];
        //         classNames.push(this.paddingClassNames);
        //         classNames.push('fa fa-lg fa-smile-o o_MessageActionView_actionReaction');
        //         return classNames.join(' ');
        //     },
        //     default: '',
        // }),

        // summary: {
        //     compute() {
        //         return sprintf(this.env._t('See who reacted with emoticon %s and react the same'), this.content);
        //     }
        // },

        // hasShowMoreButton: attr({
        //     default: false,
        // }),
    },
});
