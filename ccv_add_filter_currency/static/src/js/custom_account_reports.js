odoo.define('ccv_add_filter_currency.custom_account_reports', function (require) {
    'use strict';

    var core = require('web.core');
    var _t = core._t;
    var account_reports = require('account_reports.account_report');

    account_reports.accountReportsWidget.include({
        // Filter Tiền Tệ
        _onCurrencyChanged: function (event) {
            var selectedCurrency = $(event.target).data('currency');
            var selectedCurrency_nt = $(event.target).data('currency_nt');
            this.report_options.currency = selectedCurrency;
            this.report_options.currency = selectedCurrency_nt;
            this.reloadReportWithCurrency(selectedCurrency, selectedCurrency_nt);
        },

        reloadReportWithCurrency: function (selectedCurrency, selectedCurrency_nt) {
            var self = this;
            var currentOptions = { ...this.report_options }
            currentOptions.currency = selectedCurrency;
            currentOptions.currency_nt = selectedCurrency_nt;
            return this._rpc({
                model: this.report_model,
                method: 'get_report_informations',
                args: [this.financial_id, currentOptions],
                context: this.odoo_context,
            }).then(function (res) {
                self.parse_reports_informations(res);
                self.render();
            }).catch(function (error) {
                console.error('Failed to reload report with selected currency:', error);
            });
        },

        render_searchview_buttons: function () {
            let self = this;
            this._super(...arguments);
            // Filter tiền tệ
            var currency_button
            var a = Object.values(this.$searchview_buttons);
            for (let index = 0; index < a.length; index++) {
                if (a[index] && a[index].classList && a[index].classList.contains('o_ccv_add_filter_currency_search_template')) {
                    currency_button = a[index];
                    break;
                }
            }
            if (currency_button != undefined)
                $(currency_button).click(function (e) {
                    var el = e.target;
                    var dropdown = $(el).closest('.btn-group.dropdown');
                    var isExpanded = dropdown.find('.dropdown-toggle').attr('aria-expanded') === 'true';
                    if (isExpanded) {
                        dropdown.find('.dropdown-toggle').removeClass('show');
                        dropdown.find('.dropdown-menu').removeClass('show').css({
                            "position": "",
                            "inset": "",
                            "margin": "",
                            "transform": "",
                        });
                        dropdown.find('.dropdown-toggle').attr('aria-expanded', 'false');
                    } else {
                        dropdown.find('.dropdown-toggle').addClass('show');
                        dropdown.find('.dropdown-menu').addClass('show').css({
                            "position": "absolute",
                            "inset": "0px auto auto 0px",
                            "margin": "0px",
                            "transform": "translate(0px, 33px)",
                        });
                        dropdown.find('.dropdown-toggle').attr('aria-expanded', 'true');
                    }
                });
            $('.js_ccv_add_filter_currency_filter', this.$searchview_buttons).click(function () {
                var $el = $(this);
                for (let index = 0; index < self.report_options.currency_options.length; index++) {
                    var element = self.report_options.currency_options[index];
                    if (element.id == $el.data('id'))
                        element.selected = true;
                    else
                        element.selected = false;
                }
                self.reload();
            });
            _.each($('.js_ccv_add_filter_currency_filter', this.$searchview_buttons), function (k) {
                var el = $(k)
                var id = el.data('id');
                var selected = self.report_options['currency_options'].filter((e) => e.id == id);
                if (selected[0].selected) {
                    el.addClass('selected');
                } else {
                    el.removeClass('selected');
                }
            });

            // Filter số dư ngoại tệ
            var currency_button1 = undefined
            var a = Object.values(this.$searchview_buttons);
            for (let index = 0; index < a.length; index++) {
                if (a[index] && a[index].classList && a[index].classList.contains('o_ccv_add_column_currency_search_template')) {
                    currency_button1 = a[index];
                    break;
                }
            }
            if (currency_button1 != undefined)
                $(currency_button1).click(function (e) {
                    var el = e.target;
                    var dropdown = $(el).closest('.btn-group.dropdown');
                    var isExpanded = dropdown.find('.dropdown-toggle').attr('aria-expanded') === 'true';
                    if (isExpanded) {
                        dropdown.find('.dropdown-toggle').removeClass('show');
                        dropdown.find('.dropdown-menu').removeClass('show').css({
                            "position": "",
                            "inset": "",
                            "margin": "",
                            "transform": "",
                        });
                        dropdown.find('.dropdown-toggle').attr('aria-expanded', 'false');
                    } else {
                        dropdown.find('.dropdown-toggle').addClass('show');
                        dropdown.find('.dropdown-menu').addClass('show').css({
                            "position": "absolute",
                            "inset": "0px auto auto 0px",
                            "margin": "0px",
                            "transform": "translate(0px, 33px)",
                        });
                        dropdown.find('.dropdown-toggle').attr('aria-expanded', 'true');
                    }
                });
            $('.js_ccv_add_column_currency_filter', this.$searchview_buttons).click(function () {
                var $el = $(this);
                for (let index = 0; index < self.report_options.currency_nt_options.length; index++) {
                    var element = self.report_options.currency_nt_options[index];
                    if (element.id == $el.data('id'))
                        element.selected = true;
                    else
                        element.selected = false;
                }
                self.reload();
            });
            _.each($('.js_ccv_add_column_currency_filter', this.$searchview_buttons), function (k) {
                var el = $(k)
                var id = el.data('id');
                var selected = self.report_options['currency_nt_options'].filter((e) => e.id == id);
                if (selected[0].selected) {
                    el.addClass('selected');
                } else {
                    el.removeClass('selected');
                }
            });
        },

    });
});
