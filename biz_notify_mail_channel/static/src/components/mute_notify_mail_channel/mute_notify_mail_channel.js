/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { _lt } from 'web.core';

const { Component } = owl;

export class MuteNotifyMailChannel extends Component {

     setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    get items() {
        return [
            {id: 1, name: _lt("For 1 hour"), key: "1_hour", checked: true},
            {id: 2, name: _lt("For 4 hours"), key: "4_hours", checked: false},
            {id: 3, name: _lt("For 12 hours"), key: "12_hours", checked: false},
            {id: 4, name: _lt("For 24 hours"), key: "24_hours", checked: false},
            {id: 5, name: _lt("Until turn on"), key: "until_turn_on", checked: false}
        ];
    }

    get muteNotifyMailChannel() {
        return this.props.record;
    }

}

Object.assign(MuteNotifyMailChannel, {
    props: { record: Object },
    template: 'biz_notify_mail_channel.MuteNotifyMailChannel',
});

registerMessagingComponent(MuteNotifyMailChannel);
