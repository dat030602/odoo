odoo.define('biz_account_report_filter_account.account_report', function (require) {
'use strict';

var account_reports = require('account_reports.account_report')
var M2MFilters = account_reports.M2MFilters
var core = require('web.core');

var QWeb = core.qweb;
var _t = core._t;

account_reports.accountReportsWidget.include({
    custom_events: _.extend({}, account_reports.accountReportsWidget.prototype.custom_events, {
        'account_filter_changed': function(ev) {
             var self = this;
             self.report_options.account_ids = ev.data.account_ids;
             return self.reload().then(function () {
                 self.$searchview_buttons.find('.account_account_filter').click();
             });
        },

    }),
	init: function(parent, action) {
        console.log("this", this)
        return this._super.apply(this, arguments);
    },

    render_searchview_buttons: function() {
        this._super.apply(this, arguments);
        if (this.report_options.account) {
            if (!this.accounts_m2m_filter) {
                var fields = {};
                if ('account_ids' in this.report_options) {
                    fields['account_ids'] = {
                        label: _t('Accounts'),
                        modelName: 'account.account',
                        value: this.report_options.account_ids.map(Number),
                    };
                }
                
                if (!_.isEmpty(fields)) {
                    this.accounts_m2m_filter = new M2MFilters(this, fields, 'account_filter_changed');
                    this.accounts_m2m_filter.appendTo(this.$searchview_buttons.find('.js_account_account_m2m'));
                }
            } else {
                this.$searchview_buttons.find('.js_account_account_m2m').append(this.accounts_m2m_filter.$el);
            }
        }
    }
});
});