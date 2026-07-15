/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class SequenceVT extends Component {
    setup() {
        // Fix: async when update
        this.root = this.env.root
        this.props.record.update({
            sequence:  this.props.columnIndex
        })
    }
}

SequenceVT.template = "biz_ccv_sale.SequenceVT";
SequenceVT.supportedTypes = ["integer"];

registry.category("fields").add("sequence_vt", SequenceVT);
