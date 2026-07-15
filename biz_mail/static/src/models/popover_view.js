/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

// khong sai
registerPatch({
    name: 'PopoverView',
    fields: {
        messageReactionGroupOwnerAsReaction: one('MessageReactionGroup', {
            identifying: true,
            inverse: 'reactionPopoverView',
        }),

        messageSeenIndicatorViewOwnerAsReaction: one('MessageSeenIndicatorView', {
            identifying: true,
            inverse: 'reactionPopoverView',
        }),

        emojiPickerMessageSeenIndicatorView: one('EmojiPickerMessageSeenIndicatorView', {
            compute() {
                if (this.messageSeenIndicatorViewOwnerAsReaction) {
                    return {};
                }
                return clear();
            },
            inverse: 'popoverViewOwner',
        }),

        anchorRef: {
            compute() {
                if (this.messageReactionGroupOwnerAsReaction) {
                    return this.messageReactionGroupOwnerAsReaction.actionRef;
                }
                if (this.messageSeenIndicatorViewOwnerAsReaction) {
                    return this.messageSeenIndicatorViewOwnerAsReaction.actionRef;
                }
                return this._super()
            }
        },
        // emojiPickerView: {
        //     compute() {
        //         // if (this.composerViewOwnerAsEmoji) {
        //         //     return {};
        //         // }
        //         if (this.messageReactionGroupOwnerAsReaction) {
        //             return {};
        //         }
        //         return this._super()
        //     },
            
        // },
        emojiPickerMessageReactionView: one('EmojiPickerMessageReactionView', {
            compute() {
                if (this.messageReactionGroupOwnerAsReaction) {
                    return {};
                }
                return clear();
            },
            inverse: 'popoverViewOwner',
        }),

        content: {
            compute() {
                if (this.emojiPickerMessageReactionView) {
                    return this.emojiPickerMessageReactionView;
                }
                if (this.emojiPickerMessageSeenIndicatorView) {
                    return this.emojiPickerMessageSeenIndicatorView;
                }
                return this._super()
            }
        },
        contentClassName: {
            compute() {
                if (this.emojiPickerMessageReactionView) {
                    return 'o_PopoverView_emojiPickerView';
                }
                if (this.emojiPickerMessageSeenIndicatorView) {
                    return 'o_PopoverView_emojiPickerView';
                }
                return this._super()
            },
        },
        contentComponentName: {
            compute() {
                if (this.emojiPickerMessageReactionView) {
                    return 'EmojiPickerMessageReactionView';
                }
                if (this.emojiPickerMessageSeenIndicatorView) {
                    return 'EmojiPickerMessageSeenIndicatorView';
                }
                return this._super()
            }
        },
        position: {
            compute() {
                if (this.messageReactionGroupOwnerAsReaction) {
                    return 'top';
                }
                if (this.messageSeenIndicatorViewOwnerAsReaction) {
                    return 'top';
                }
                return this._super()
            },
        },
        // demo
        

    }
});
