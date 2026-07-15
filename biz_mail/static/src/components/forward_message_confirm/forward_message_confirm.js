/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update';
const { Component, useRef } = owl;



export class ForwardMessageConfirm extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        // useUpdate({ func: () => this._update() });
        /**
         * Reference to element containing the prettyBody. Useful to be able to
         * replace prettyBody with new value in JS (which is faster than t-raw).
         */
        this._prettyBodyRef = useRef('prettyBody');
        /**
         * Reference to the content of the message.
         */
        this._contentRef = useRef('content');
    }

    // _insertReadMoreLess($element) {
    //     const groups = [];
    //     let readMoreNodes;

    //     // nodeType 1: element_node
    //     // nodeType 3: text_node
    //     const $children = $element.contents()
    //         .filter((index, content) =>
    //             content.nodeType === 1 || (content.nodeType === 3 && content.nodeValue.trim())
    //         );

    //     for (const child of $children) {
    //         let $child = $(child);

    //         // Hide Text nodes if "stopSpelling"
    //         if (
    //             child.nodeType === 3 &&
    //             $child.prevAll('[id*="stopSpelling"]').length > 0
    //         ) {
    //             // Convert Text nodes to Element nodes
    //             $child = $('<span>', {
    //                 text: child.textContent,
    //                 'data-o-mail-quote': '1',
    //             });
    //             child.parentNode.replaceChild($child[0], child);
    //         }

    //         // Create array for each 'read more' with nodes to toggle
    //         if (
    //             $child.attr('data-o-mail-quote') ||
    //             (
    //                 $child.get(0).nodeName === 'BR' &&
    //                 $child.prev('[data-o-mail-quote="1"]').length > 0
    //             )
    //         ) {
    //             if (!readMoreNodes) {
    //                 readMoreNodes = [];
    //                 groups.push(readMoreNodes);
    //             }
    //             $child.hide();
    //             readMoreNodes.push($child);
    //         } else {
    //             readMoreNodes = undefined;
    //             this._insertReadMoreLess($child);
    //         }
    //     }

    //     for (const group of groups) {
    //         const index = this._lastReadMoreIndex++;
    //         // Insert link just before the first node
    //         const $readMoreLess = $('<a>', {
    //             class: 'o_Message_readMoreLess d-block',
    //             href: '#',
    //             text: READ_MORE,
    //         }).insertBefore(group[0]);

    //         // Toggle All next nodes
    //         if (!this._isReadMoreByIndex.has(index)) {
    //             this._isReadMoreByIndex.set(index, true);
    //         }
    //         const updateFromState = () => {
    //             const isReadMore = this._isReadMoreByIndex.get(index);
    //             for (const $child of group) {
    //                 $child.hide();
    //                 $child.toggle(!isReadMore);
    //             }
    //             $readMoreLess.text(isReadMore ? READ_MORE : READ_LESS);
    //         };
    //         $readMoreLess.click(e => {
    //             e.preventDefault();
    //             this._isReadMoreByIndex.set(index, !this._isReadMoreByIndex.get(index));
    //             updateFromState();
    //         });
    //         updateFromState();
    //     }
    // }

    // _update() {
    //     
    //     if (this._prettyBodyRef.el && this.messageView.message.prettyBody !== this._lastPrettyBody) {
    //         this._prettyBodyRef.el.innerHTML = this.messageView.message.prettyBody;
    //         this._lastPrettyBody = this.messageView.message.prettyBody;
    //     }
    //     if (!this._prettyBodyRef.el) {
    //         this._lastPrettyBody = undefined;
    //     }
    //     // Remove all readmore before if any before reinsert them with _insertReadMoreLess.
    //     // This is needed because _insertReadMoreLess is working with direct DOM mutations
    //     // which are not sync with Owl.
    //     if (this._contentRef.el) {
    //         for (const el of [...this._contentRef.el.querySelectorAll(':scope .o_Message_readMoreLess')]) {
    //             el.remove();
    //         }
    //         this._lastReadMoreIndex = 0;
    //         this._insertReadMoreLess($(this._contentRef.el));
    //         this.messaging.messagingBus.trigger('o-component-message-read-more-less-inserted', {
    //             message: this.messageView.message,
    //         });
    //     }
    // }

    /**
     * @returns {ForwardMessageConfirmView}
     */
    get forwardMessageConfirmView() {
        return this.props.record;
    }

}

Object.assign(ForwardMessageConfirm, {
    props: { record: Object },
    template: 'mail.ForwardMessageConfirm',
});

registerMessagingComponent(ForwardMessageConfirm);
