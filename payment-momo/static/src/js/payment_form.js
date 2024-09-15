/** @odoo-module **/

import paymentForm from '@payment/js/payment_form';
import { _t } from "@web/core/l10n/translation";
import { jsonrpc, RPCError } from "@web/core/network/rpc_service";

paymentForm.include({

    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of momo for direct payment.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'momo') {
            this._super(...arguments);
            return;
        }
        this._setPaymentFlow('direct');
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Simulate a feedback from a payment provider and redirect the customer to the status page.
     *
     * @override method from payment.payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'momo') {
            this._super(...arguments);
            return;
        }

    jsonrpc("/payment/momo/payment-generate-url/", {
      payload: processingValues.data.payload,
      reference: processingValues.reference,
    })
      .then((data) => {
        const url = JSON.parse(data)['payUrl'];
        console.log(url);
        window.location.href = url;
      })
      .catch((error) => {
        if (error instanceof RPCError) {
          this._displayErrorDialog(
            _t("Payment processing failed"),
            error.data.message
          );
          this._enableButton?.(); // This method doesn't exists in Express Checkout form.
        } else {
          return Promise.reject(error);
        }
      });
    },

});
