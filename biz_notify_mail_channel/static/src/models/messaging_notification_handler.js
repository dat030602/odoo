/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from "@mail/model/model_field_command";
import { escape, sprintf } from '@web/core/utils/strings';
import { htmlToTextContentInline } from '@mail/js/utils';
import { increment } from '@mail/model/model_field_command';

const PREVIEW_MSG_MAX_SIZE = 350; // optimal for native English speakers


registerPatch({
    name: "MessagingNotificationHandler",
    recordMethods: {
        async _handleNotificationChannelMessage({ id: channelId, message: messageData }) {
            let channel = this.messaging.models['Channel'].findFromIdentifyingData({ id: channelId });
            let isTypeChannel = channel && channel.channel_type === "channel" ? true : false;
            if(channel.thread.isMuteNotify || isTypeChannel) {
                if (!channel && this.messaging.isCurrentUserGuest) {
                    return; // guests should not receive messages for channels they don't know, and they can't make the channel_info RPC
                }
                const convertedData = this.messaging.models['Message'].convertData(messageData);

                // Fetch missing info from channel before going further. Inserting
                // a channel with incomplete info can lead to issues. This is in
                // particular the case with the `uuid` field that is assumed
                // "required" by the rest of the code and is necessary for some
                // features such as chat windows.
                if (!channel || !channel.channel_type) {
                    const res = await this.messaging.models['Thread'].performRpcChannelInfo({ ids: [channelId] });
                    if (!this.exists()) {
                        return;
                    }
                    channel = res[0].channel;
                }
                if (!channel.thread.isPinned) {
                    channel.thread.pin();
                }

                const message = this.messaging.models['Message'].insert(convertedData);
                this._notifyThreadViewsMessageReceived(message);

                // If the current partner is author, do nothing else.
                if (message.author === this.messaging.currentPartner) {
                    return;
                }

                // Chat from OdooBot is considered disturbing and should only be
                // shown on the menu, but no notification and no thread open.
                const isChatWithOdooBot = (
                    channel.correspondent &&
                    channel.correspondent === this.messaging.partnerRoot
                );
                if (!isChatWithOdooBot) {
                    const isOdooFocused = this.env.services['presence'].isOdooFocused();
                    // Notify if out of focus
                    if (!isOdooFocused && !channel.thread.isMuteNotify) {
                        this._notifyNewChannelMessageWhileOutOfFocus({
                            channel,
                            message,
                        });
                    }
                    if (!this.messaging.currentGuest) {
                        // disabled on non-channel threads and
                        // on `channel` channels for performance reasons
                        channel.thread.markAsFetched();
                    }
                    // open chat on receiving new message if it was not already opened or folded
                    if (!this.messaging.device.isSmall && !channel.thread.chatWindow && !channel.thread.isMuteNotify) {
                        this.messaging.chatWindowManager.openThread(channel.thread);
                    }
                }
            } else {
                return this._super(...arguments);
            }
        },

        _notifyNewChannelMessageWhileOutOfFocus({ channel, message }) {
            if(channel && channel.channel_type === 'channel') {
                const author = message.author;
                const messaging = this.messaging;
                let notificationTitle;
                if (!author) {
                    notificationTitle = this.env._t("New message");
                } else {
                    // hack: notification template does not support OWL components,
                    // so we simply use their template to make HTML as if it comes
                    // from component
                    const channelName = channel.thread.displayName;
                    const channelNameWithIcon = channelName;
                    notificationTitle = sprintf(
                        this.env._t("%s from %s"),
                        author.nameOrDisplayName,
                        channelNameWithIcon
                    );
                }
                const notificationContent = escape(
                    htmlToTextContentInline(message.body).substr(0, PREVIEW_MSG_MAX_SIZE)
                );
                this.messaging.userNotificationManager.sendNotification({
                    message: notificationContent,
                    title: notificationTitle,
                    type: 'info',
                });
                messaging.update({ outOfFocusUnreadMessageCounter: increment() });
                const titlePattern = messaging.outOfFocusUnreadMessageCounter === 1
                    ? this.env._t("%s Message")
                    : this.env._t("%s Messages");
                this.env.bus.trigger('set_title_part', {
                    part: '_chat',
                    title: sprintf(titlePattern, messaging.outOfFocusUnreadMessageCounter),
                });
            } else {
                return this._super(...arguments);
            }
        },
    }
})