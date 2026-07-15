/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DiscussContainer } from '@mail/components/discuss_container/discuss_container';

import { useModels } from '@mail/component_hooks/use_models';
// ensure component is registered before-hand
import '@mail/components/discuss/discuss';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component, onWillDestroy } = owl;


patch(DiscussContainer.prototype, "CustomDiscussContainer", {
    setup() {
        const { action } = this.props;
        if(action !== undefined && action.params && action.params.active_id) {
            useModels();
            onWillDestroy(() => this._willDestroy());
            this.env.services.messaging.modelManager.messagingCreatedPromise.then(async () => {
                const initActiveId =
                    (action.context && action.context.active_id) ||
                    (action.params && action.params.default_active_id) ||
                    (action.params && action.params.active_id) ||
                    'mail.box_inbox';
                this.discuss = this.messaging.discuss;
                this.discuss.update({
                    discussView: {
                        actionId: action.id,
                    },
                    initActiveId,
                });
                await this.messaging.initializedPromise;
                if (!this.discuss.isInitThreadHandled) {
                    this.discuss.update({ isInitThreadHandled: true });
                    if (!this.discuss.activeThread) {
                        this.discuss.openInitThread();
                    }
                } else if(this.discuss.isInitThreadHandled) {
                    if (!this.discuss.activeThread) {
                        this.discuss.openInitThread();
                    }
                }
            });
            DiscussContainer.currentInstance = this;
        } else {
            this._super.apply();
        }
    },
})