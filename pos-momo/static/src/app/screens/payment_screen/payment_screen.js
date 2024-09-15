/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { qrCodeSrc } from "@point_of_sale/utils";
import { useService } from "@web/core/utils/hooks";
import { PaymentOnlinePaymentPopup } from "@pos_momo/app/utils/online_payment_popup/online_payment_popup";

patch(PaymentScreen.prototype, {
  setup() {
    super.setup();
    this.rpc = useService("rpc");
    
  },
  //@override
  async _isOrderValid(isForceValidate) {
    if (!(await super._isOrderValid(...arguments))) {
      return false;
    }

    if (!this.payment_methods_from_config.some((pm) => pm.is_online_payment)) {
      return true;
    }

    if (this.currentOrder.finalized) {
      this.afterOrderValidation(false);
      return false;
    }
    const onlinePaymentLines = this.getRemainingOnlinePaymentLines();
    if (onlinePaymentLines.length > 0) {
      // Send the order to the server everytime before the online payments process to
      // allow the server to get the data for online payments and link the successful
      // online payments to the order.
      // The validation process will be done by the server directly after a successful
      // online payment that makes the order fully paid.
      this.currentOrder.date_order = luxon.DateTime.now();
      this.currentOrder.save_to_db();
      this.pos.addOrderToUpdateSet();

      try {
        await this.pos.sendDraftToServer();
      } catch (error) {
        // Code from _finalizeValidation():
        if (error.code == 700 || error.code == 701) {
          this.error = true;
        }

        if ("code" in error) {
          // We started putting `code` in the rejected object for invoicing error.
          // We can continue with that convention such that when the error has `code`,
          // then it is an error when invoicing. Besides, _handlePushOrderError was
          // introduce to handle invoicing error logic.
          await this._handlePushOrderError(error);
        }
        this.showSaveOrderOnServerErrorPopup();
        return false;
      }

      if (!this.currentOrder.server_id) {
        this.showSaveOrderOnServerErrorPopup();
        return false;
      }

      if (!this.currentOrder.server_id) {
        this.cancelOnlinePayment(this.currentOrder);
        this.popup.add(ErrorPopup, {
          title: _t("Online payment unavailable"),
          body: _t("The QR Code for paying could not be generated."),
        });
        return false;
      }

      var qrCodeImgSrc = "";
      let payment_method = this.currentOrder.get_paymentlines()[0].name;
      if (payment_method.indexOf("Momo") !== -1) {
        var amount = 0;
        for (const onlinePaymentLine of onlinePaymentLines) amount = onlinePaymentLine.get_amount();
        const response = await this.rpc("/payment/pos/momo/payment-generate-url", {
          amount: amount,
          reference: `${this.currentOrder.uid}-HD${this.currentOrder.pos_session_id}-${this.currentOrder.server_id}-${this.currentOrder.access_token}`,
        });

        let qrcode = JSON.parse(response);
        qrCodeImgSrc = qrcode["qrCodeUrl"];
      } else {
        qrCodeImgSrc = `${this.pos.base_url}/pos/pay/${this.currentOrder.server_id}?access_token=${this.currentOrder.access_token}`;
      }
      qrCodeImgSrc = qrCodeImgSrc.replace(/\//g, "_");
      qrCodeImgSrc = qrCodeSrc(qrCodeImgSrc);
      // Component.env.bus.addEventListener(`pos_session-${this.currentOrder.id}-${this.currentOrder.access_token}`, (ev) => console.log(ev));

      let prevOnlinePaymentLine = null;
      let lastOrderServerOPData = null;
      for (const onlinePaymentLine of onlinePaymentLines) {
        const onlinePaymentLineAmount = onlinePaymentLine.get_amount();
        // The local state is not aware if the online payment has already been done.
        lastOrderServerOPData = await this.currentOrder.update_online_payments_data_with_server(
          this.pos.orm,
          onlinePaymentLineAmount
        );
        if (!lastOrderServerOPData) {
          this.popup.add(ErrorPopup, {
            title: _t("Online payment unavailable"),
            body: _t("There is a problem with the server. The order online payment status cannot be retrieved."),
          });
          return false;
        }
        if (!lastOrderServerOPData.is_paid) {
          if (lastOrderServerOPData.modified_payment_lines) {
            this.cancelOnlinePayment(this.currentOrder);
            this.showModifiedOnlinePaymentsPopup();
            return false;
          }
          if (
            (prevOnlinePaymentLine && prevOnlinePaymentLine.get_payment_status() !== "done") ||
            !this.checkRemainingOnlinePaymentLines(lastOrderServerOPData.amount_unpaid)
          ) {
            this.cancelOnlinePayment(this.currentOrder);
            return false;
          }

          onlinePaymentLine.set_payment_status("waiting");
          this.currentOrder.select_paymentline(onlinePaymentLine);

          // ---------------------------

          if (!this.currentOrder.uiState.PaymentScreen) {
            this.currentOrder.uiState.PaymentScreen = {};
          }
          this.currentOrder.uiState.PaymentScreen.onlinePaymentData = {
            amount: onlinePaymentLineAmount,
            qrCode: qrCodeImgSrc,
            order: this.currentOrder,
          };
          const { confirmed, payload: orderServerOPData } = await this.popup.add(
            PaymentOnlinePaymentPopup,
            this.currentOrder.uiState.PaymentScreen.onlinePaymentData
          );
          if (this.currentOrder.uiState.PaymentScreen) {
            delete this.currentOrder.uiState.PaymentScreen.onlinePaymentData;
            if (Object.keys(this.currentOrder.uiState.PaymentScreen).length === 0) {
              delete this.currentOrder.uiState.PaymentScreen;
            }
          }
          lastOrderServerOPData = confirmed ? orderServerOPData : null;

          // ---------------------------

          // lastOrderServerOPData = await this.showOnlinePaymentQrCode(qrCodeImgSrc, onlinePaymentLineAmount);
          if (onlinePaymentLine.get_payment_status() === "waiting") {
            onlinePaymentLine.set_payment_status(undefined);
          }
          if (payment_method.indexOf("Momo") !== -1) {
            const response = await this.rpc("/payment/pos/momo/payment-check-transaction", {
              orderID: `${this.currentOrder.uid}`,
              reference: `${this.currentOrder.uid}-HD${this.currentOrder.pos_session_id}-${this.currentOrder.server_id}-${this.currentOrder.access_token}`,
            });
            const payload = JSON.parse(response);
            if (payload["resultCode"] == 0) {
              onlinePaymentLine.set_payment_status("done");
            } else if (payload["resultCode"] == 1000) {
              this.popup.add(ErrorPopup, {
                title: _t("Error Online payment"),
                body: _t("Giao dịch đang thực hiện"),
              });
            } else if (payload["resultCode"] == 1005) {
              this.popup.add(ErrorPopup, {
                title: _t("Error Online payment"),
                body: _t("Giao dịch đã hết hạn"),
              });
            } else if (payload["resultCode"] == 1003 || payload["resultCode"] == 1017) {
              this.popup.add(ErrorPopup, {
                title: _t("Error Online payment"),
                body: _t("Giao dịch đã huỷ"),
              });
            } else {
              this.popup.add(ErrorPopup, {
                title: _t("Error Online payment"),
                body: _t("Lỗi giao dịch"),
              });
            }
            prevOnlinePaymentLine = onlinePaymentLine;
            if (payload["resultCode"] == 0) {
              this.currentOrder.finalized = true;
              let syncOrderResult;
              syncOrderResult = await this.pos.push_single_order(this.currentOrder);
              await this._finalizeValidation();
              if (syncOrderResult && syncOrderResult.length > 0 && this.currentOrder.wait_for_push_order()) {
                console.log("RUN1");
                await this.postPushOrderResolve(syncOrderResult.map((res) => res.id));
                await this.afterOrderValidation(!!syncOrderResult && syncOrderResult.length > 0);
                return false;
              }
            }
          }
        }
      }

      if (!lastOrderServerOPData || !lastOrderServerOPData.is_paid) {
        lastOrderServerOPData = await this.currentOrder.update_online_payments_data_with_server(this.pos.orm, 0);
      }
      if (!lastOrderServerOPData || !lastOrderServerOPData.is_paid) {
        return false;
      }

      await this.afterPaidOrderSavedOnServer(lastOrderServerOPData.paid_order);
      return false; // Cancel normal flow because the current order is already saved on the server.
    } else if (this.currentOrder.server_id) {
      const orderServerOPData = await this.currentOrder.update_online_payments_data_with_server(this.pos.orm, 0);
      if (!orderServerOPData) {
        const { confirmed } = await this.popup.add(ConfirmPopup, {
          title: _t("Online payment unavailable"),
          body: _t(
            "There is a problem with the server. The order online payment status cannot be retrieved. Are you sure there is no online payment for this order ?"
          ),
          confirmText: _t("Yes"),
        });
        return confirmed;
      }
      if (orderServerOPData.is_paid) {
        await this.afterPaidOrderSavedOnServer(orderServerOPData.paid_order);
        return false; // Cancel normal flow because the current order is already saved on the server.
      }
      if (orderServerOPData.modified_payment_lines) {
        this.showModifiedOnlinePaymentsPopup();
        return false;
      }
    }

    return true;
  },
});
