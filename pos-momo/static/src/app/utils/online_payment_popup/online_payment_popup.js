/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useService } from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

export class PaymentOnlinePaymentPopup extends AbstractAwaitablePopup {
  static template = "pos_momo.OnlinePaymentPopup";

  setup() {
    super.setup();
    if (this.props.order.uiState.PaymentScreen) {
      this.props.order.uiState.PaymentScreen.onlinePaymentPopup = this;
    }
    this.rpc = useService("rpc");
  }
  setReceivedOrderServerOPData(opData) {
    this.opData = opData;
    this.confirm();
  }
  async confirm() {
    super.confirm();
    delete this.props.order.uiState.PaymentScreen?.onlinePaymentPopup;
  }
  cancel() {
    super.cancel();
    delete this.props.order.uiState.PaymentScreen?.onlinePaymentPopup;
  }
  async getPayload() {
    return this.opData;
  }
  async check_transaction() {
    console.log(this);

    this.cancel();
    return true;
  }
}