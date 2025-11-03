/* Part of Odoo. See LICENSE file for full copyright and licensing details. */

odoo.define('payment_vnpay_token.payment_form', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');
    var core = require('web.core');

    var _t = core._t;

    publicWidget.registry.PaymentVNPayTokenForm = publicWidget.Widget.extend({
        selector: '.payment_vnpay_token_form',
        events: {
            'click #pay_with_token': '_onPayWithToken',
            'click #create_token': '_onCreateToken',
            'click #delete_token': '_onDeleteToken',
            'change #token': '_onTokenChange',
        },

        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.provider = options.provider;
            this.paymentForm = options.paymentForm;
        },

        start: function () {
            this._super.apply(this, arguments);
            this._loadSavedTokens();
        },

        _loadSavedTokens: function () {
            var self = this;
            ajax.jsonRpc('/payment/vnpay_token/get-tokens/', 'call', {})
                .then(function (result) {
                    if (result.success) {
                        self._populateTokenSelect(result.tokens);
                    }
                })
                .catch(function (error) {
                    console.error('Error loading tokens:', error);
                });
        },

        _populateTokenSelect: function (tokens) {
            var tokenSelect = this.$('#token');
            tokenSelect.empty();
            tokenSelect.append('<option value="">Select a saved token...</option>');
            
            tokens.forEach(function (token) {
                var option = $('<option></option>')
                    .attr('value', token.id)
                    .text(token.card_number + ' (' + token.bank_code + ')');
                tokenSelect.append(option);
            });
        },

        _onPayWithToken: function (ev) {
            ev.preventDefault();
            
            var tokenId = this.$('#token').val();
            var amount = this.$('#amount').val();
            var currency = this.$('#currency').val();
            
            if (!tokenId || !amount) {
                this._showError('Please select a token and enter an amount');
                return;
            }
            
            this._processPayment(tokenId, amount, currency);
        },

        _onCreateToken: function (ev) {
            ev.preventDefault();
            window.location.href = '/payment/vnpay_token/create-token/';
        },

        _onDeleteToken: function (ev) {
            ev.preventDefault();
            
            var tokenId = this.$('#token').val();
            if (!tokenId) {
                this._showError('Please select a token to delete');
                return;
            }
            
            if (!confirm('Are you sure you want to delete this token?')) {
                return;
            }
            
            this._deleteToken(tokenId);
        },

        _onTokenChange: function (ev) {
            var tokenId = this.$('#token').val();
            if (tokenId) {
                this.$('#delete_token').prop('disabled', false);
            } else {
                this.$('#delete_token').prop('disabled', true);
            }
        },

        _processPayment: function (tokenId, amount, currency) {
            var self = this;
            this._showLoading();
            
            ajax.jsonRpc('/payment/vnpay_token/pay-with-token/', 'call', {
                token_id: tokenId,
                amount: parseFloat(amount),
                currency_id: currency,
            })
                .then(function (result) {
                    if (result.success) {
                        // Use a safer redirect method to avoid cross-origin issues
                        try {
                            if (window.top && window.top !== window) {
                                // If we're in an iframe, redirect the top window
                                window.top.location.href = result.payment_url;
                            } else {
                                // Normal redirect
                                window.location.href = result.payment_url;
                            }
                        } catch (error) {
                            // Fallback to normal redirect if cross-origin access fails
                            console.warn('Cross-origin redirect failed, using fallback:', error);
                            window.location.href = result.payment_url;
                        }
                    } else {
                        self._showError('Payment failed: ' + result.error);
                    }
                })
                .catch(function (error) {
                    console.error('Error processing payment:', error);
                    self._showError('Payment failed. Please try again.');
                })
                .always(function () {
                    self._hideLoading();
                });
        },

        _deleteToken: function (tokenId) {
            var self = this;
            this._showLoading();
            
            ajax.jsonRpc('/payment/vnpay_token/delete-token/', 'call', {
                token_id: tokenId,
            })
                .then(function (result) {
                    if (result.success) {
                        self._showSuccess('Token deleted successfully');
                        self._loadSavedTokens();
                    } else {
                        self._showError('Failed to delete token: ' + result.error);
                    }
                })
                .catch(function (error) {
                    console.error('Error deleting token:', error);
                    self._showError('Failed to delete token. Please try again.');
                })
                .always(function () {
                    self._hideLoading();
                });
        },

        _showLoading: function () {
            this.$('.payment_vnpay_token_form_actions').append(
                '<div class="payment_vnpay_token_loading">Processing...</div>'
            );
        },

        _hideLoading: function () {
            this.$('.payment_vnpay_token_loading').remove();
        },

        _showError: function (message) {
            this._showMessage(message, 'error');
        },

        _showSuccess: function (message) {
            this._showMessage(message, 'success');
        },

        _showMessage: function (message, type) {
            var messageClass = 'payment_vnpay_token_message payment_vnpay_token_message_' + type;
            var messageDiv = $('<div class="' + messageClass + '">' + message + '</div>');
            
            this.$('.payment_vnpay_token_form_content').prepend(messageDiv);
            
            setTimeout(function () {
                messageDiv.fadeOut(function () {
                    messageDiv.remove();
                });
            }, 3000);
        },
    });

    publicWidget.registry.PaymentVNPayTokenCreateForm = publicWidget.Widget.extend({
        selector: '.payment_vnpay_token_create_form',
        events: {
            'click #create_token_btn': '_onCreateToken',
            'click #cancel_create_token': '_onCancelCreateToken',
        },

        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.provider = options.provider;
        },

        _onCreateToken: function (ev) {
            ev.preventDefault();
            this._createToken();
        },

        _onCancelCreateToken: function (ev) {
            ev.preventDefault();
            window.location.href = '/payment/status';
        },

        _createToken: function () {
            var self = this;
            this._showLoading();
            
            ajax.jsonRpc('/payment/vnpay_token/create-token/', 'call', {})
                .then(function (result) {
                    if (result.success) {
                        // Use a safer redirect method to avoid cross-origin issues
                        try {
                            if (window.top && window.top !== window) {
                                // If we're in an iframe, redirect the top window
                                window.top.location.href = result.token_url;
                            } else {
                                // Normal redirect
                                window.location.href = result.token_url;
                            }
                        } catch (error) {
                            // Fallback to normal redirect if cross-origin access fails
                            console.warn('Cross-origin redirect failed, using fallback:', error);
                            window.location.href = result.token_url;
                        }
                    } else {
                        self._showError('Token creation failed: ' + result.error);
                    }
                })
                .catch(function (error) {
                    console.error('Error creating token:', error);
                    self._showError('Token creation failed. Please try again.');
                })
                .always(function () {
                    self._hideLoading();
                });
        },

        _showLoading: function () {
            this.$('.payment_vnpay_token_create_form_actions').append(
                '<div class="payment_vnpay_token_loading">Creating token...</div>'
            );
        },

        _hideLoading: function () {
            this.$('.payment_vnpay_token_loading').remove();
        },

        _showError: function (message) {
            this._showMessage(message, 'error');
        },

        _showMessage: function (message, type) {
            var messageClass = 'payment_vnpay_token_message payment_vnpay_token_message_' + type;
            var messageDiv = $('<div class="' + messageClass + '">' + message + '</div>');
            
            this.$('.payment_vnpay_token_create_form_content').prepend(messageDiv);
            
            setTimeout(function () {
                messageDiv.fadeOut(function () {
                    messageDiv.remove();
                });
            }, 3000);
        },
    });

    return {
        PaymentVNPayTokenForm: publicWidget.registry.PaymentVNPayTokenForm,
        PaymentVNPayTokenCreateForm: publicWidget.registry.PaymentVNPayTokenCreateForm,
    };
});
