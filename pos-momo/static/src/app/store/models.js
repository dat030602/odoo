/** @odoo-module */

import { serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { Order, Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(Order.prototype, {
  export_as_JSON() {
    var orderLines, paymentLines;
    orderLines = [];
    this.orderlines.forEach((item) => {
      return orderLines.push([0, 0, item.export_as_JSON()]);
    });
    paymentLines = [];
    this.paymentlines.forEach((item) => {
      let itemAsJson;
      if (item.payment_status != "done") itemAsJson = item.export_as_JSON();
      else
        itemAsJson = {
          name: serializeDateTime(DateTime.local()),
          payment_method_id: item.payment_method.id,
          amount: item.get_amount(),
          payment_status: item.payment_status,
          can_be_reversed: item.can_be_reversed,
          ticket: item.ticket,
          card_type: item.card_type,
          cardholder_name: item.cardholder_name,
          transaction_id: item.transaction_id,
        };
      if (itemAsJson) {
        return paymentLines.push([0, 0, itemAsJson]);
      }
    });
    var json = {
      name: this.get_name(),
      amount_paid: this.get_total_paid() - this.get_change(),
      amount_total: this.get_total_with_tax(),
      amount_tax: this.get_total_tax(),
      amount_return: this.get_change(),
      lines: orderLines,
      statement_ids: paymentLines,
      pos_session_id: this.pos_session_id,
      pricelist_id: this.pricelist ? this.pricelist.id : false,
      partner_id: this.get_partner() ? this.get_partner().id : false,
      user_id: this.pos.user.id,
      uid: this.uid,
      sequence_number: this.sequence_number,
      date_order: serializeDateTime(this.date_order),
      fiscal_position_id: this.fiscal_position ? this.fiscal_position.id : false,
      server_id: this.server_id ? this.server_id : false,
      to_invoice: this.to_invoice ? this.to_invoice : false,
      shipping_date: this.shippingDate ? this.shippingDate : false,
      is_tipped: this.is_tipped || false,
      tip_amount: this.tip_amount || 0,
      access_token: this.access_token || "",
      last_order_preparation_change: JSON.stringify(this.lastOrderPrepaChange),
      ticket_code: this.ticketCode || "",
    };
    if (!this.is_paid && this.user_id) {
      json.user_id = this.user_id;
    }
    return json;
  },
});