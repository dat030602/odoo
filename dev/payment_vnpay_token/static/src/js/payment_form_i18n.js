/* Part of Odoo. See LICENSE file for full copyright and licensing details. */

odoo.define('payment_vnpay_token.payment_form_i18n', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');
    var core = require('web.core');

    var _t = core._t;

    // Vietnamese translations
    var translations = {
        'vi': {
            'Select a saved token...': 'Chọn token đã lưu...',
            'Please select a token and enter an amount': 'Vui lòng chọn token và nhập số tiền',
            'Payment failed: ': 'Thanh toán thất bại: ',
            'Payment failed. Please try again.': 'Thanh toán thất bại. Vui lòng thử lại.',
            'Please select a token to delete': 'Vui lòng chọn token để xóa',
            'Are you sure you want to delete this token?': 'Bạn có chắc chắn muốn xóa token này?',
            'Token deleted successfully': 'Token đã được xóa thành công',
            'Failed to delete token: ': 'Không thể xóa token: ',
            'Failed to delete token. Please try again.': 'Không thể xóa token. Vui lòng thử lại.',
            'Processing...': 'Đang xử lý...',
            'Token creation failed: ': 'Tạo token thất bại: ',
            'Token creation failed. Please try again.': 'Tạo token thất bại. Vui lòng thử lại.',
            'Creating token...': 'Đang tạo token...',
            'Pay with Token': 'Thanh toán với Token',
            'Create New Token': 'Tạo Token Mới',
            'Delete Selected Token': 'Xóa Token Đã Chọn',
            'Create Token': 'Tạo Token',
            'Cancel': 'Hủy',
            'Amount': 'Số tiền',
            'Currency': 'Tiền tệ',
            'Select Token': 'Chọn Token',
        }
    };

    function getTranslation(key, lang) {
        lang = lang || document.documentElement.lang || 'en';
        return translations[lang] && translations[lang][key] || key;
    }

    function isVietnamese() {
        return document.documentElement.lang === 'vi' || 
               document.querySelector('html[lang="vi"]') !== null ||
               navigator.language.startsWith('vi');
    }

    publicWidget.registry.PaymentVNPayTokenFormI18n = publicWidget.Widget.extend({
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
            this._setupTranslations();
        },

        _setupTranslations: function () {
            // Update form labels if Vietnamese
            if (isVietnamese()) {
                this.$('label[for="amount"]').text(getTranslation('Amount', 'vi'));
                this.$('label[for="currency"]').text(getTranslation('Currency', 'vi'));
                this.$('label[for="token"]').text(getTranslation('Select Token', 'vi'));
                this.$('#pay_with_token').text(getTranslation('Pay with Token', 'vi'));
                this.$('#create_token').text(getTranslation('Create New Token', 'vi'));
                this.$('#delete_token').text(getTranslation('Delete Selected Token', 'vi'));
            }
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
            var selectText = getTranslation('Select a saved token...', isVietnamese() ? 'vi' : 'en');
            tokenSelect.append('<option value="">' + selectText + '</option>');
            
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
                var message = getTranslation('Please select a token and enter an amount', isVietnamese() ? 'vi' : 'en');
                this._showError(message);
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
                var message = getTranslation('Please select a token to delete', isVietnamese() ? 'vi' : 'en');
                this._showError(message);
                return;
            }
            
            var confirmMessage = getTranslation('Are you sure you want to delete this token?', isVietnamese() ? 'vi' : 'en');
            if (!confirm(confirmMessage)) {
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
                        var message = getTranslation('Payment failed: ', isVietnamese() ? 'vi' : 'en') + result.error;
                        self._showError(message);
                    }
                })
                .catch(function (error) {
                    console.error('Error processing payment:', error);
                    var message = getTranslation('Payment failed. Please try again.', isVietnamese() ? 'vi' : 'en');
                    self._showError(message);
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
                        var message = getTranslation('Token deleted successfully', isVietnamese() ? 'vi' : 'en');
                        self._showSuccess(message);
                        self._loadSavedTokens();
                    } else {
                        var message = getTranslation('Failed to delete token: ', isVietnamese() ? 'vi' : 'en') + result.error;
                        self._showError(message);
                    }
                })
                .catch(function (error) {
                    console.error('Error deleting token:', error);
                    var message = getTranslation('Failed to delete token. Please try again.', isVietnamese() ? 'vi' : 'en');
                    self._showError(message);
                })
                .always(function () {
                    self._hideLoading();
                });
        },

        _showLoading: function () {
            var loadingText = getTranslation('Processing...', isVietnamese() ? 'vi' : 'en');
            this.$('.payment_vnpay_token_form_actions').append(
                '<div class="payment_vnpay_token_loading">' + loadingText + '</div>'
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

    publicWidget.registry.PaymentVNPayTokenCreateFormI18n = publicWidget.Widget.extend({
        selector: '.payment_vnpay_token_create_form',
        events: {
            'click #create_token_btn': '_onCreateToken',
            'click #cancel_create_token': '_onCancelCreateToken',
        },

        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.provider = options.provider;
            this._setupTranslations();
        },

        _setupTranslations: function () {
            // Update form labels if Vietnamese
            if (isVietnamese()) {
                this.$('#create_token_btn').text(getTranslation('Create Token', 'vi'));
                this.$('#cancel_create_token').text(getTranslation('Cancel', 'vi'));
            }
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
                        var message = getTranslation('Token creation failed: ', isVietnamese() ? 'vi' : 'en') + result.error;
                        self._showError(message);
                    }
                })
                .catch(function (error) {
                    console.error('Error creating token:', error);
                    var message = getTranslation('Token creation failed. Please try again.', isVietnamese() ? 'vi' : 'en');
                    self._showError(message);
                })
                .always(function () {
                    self._hideLoading();
                });
        },

        _showLoading: function () {
            var loadingText = getTranslation('Creating token...', isVietnamese() ? 'vi' : 'en');
            this.$('.payment_vnpay_token_create_form_actions').append(
                '<div class="payment_vnpay_token_loading">' + loadingText + '</div>'
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
        PaymentVNPayTokenFormI18n: publicWidget.registry.PaymentVNPayTokenFormI18n,
        PaymentVNPayTokenCreateFormI18n: publicWidget.registry.PaymentVNPayTokenCreateFormI18n,
    };
});
