odoo.define('biz_org_chart.OrgChartModel', function(require) {
    'use strict';

    var AbstractModel = require('web.AbstractModel');

    var OrgChartModel = AbstractModel.extend({
        /**
         * @override
         * @param {Widget} parent
         */
        init: function() {
            this._super.apply(this, arguments);
            this.data = null;
        },

        get: function() {
            return {
                records: this.records,
            };
        },

        load: function(params) {
            return this._load(params);
        },

        reload: function(id, params) {
            return this._load(params);
        },

        _load: function(params) {
            this.domain = params.domain || this.domain || [];
            var context = params.context || {};
            if (this.domain) {
                context.org_chart = true;
            }
            this.modelName = params.modelName || this.modelName || "";
            var self = this;
            this.records = [];
            return this._rpc({
                model: this.modelName,
                method: 'search_read',
                fields: [],
                domain: this.domain,
                context: context,

            }).then(function(result) {
                self.records = result;
            });
        },
    });

    return OrgChartModel;

});