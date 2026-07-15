odoo.define('ccv_sql.reconciliation_date_filter', function (require) {
"use strict";

var ReconciliationRenderer = require('account.ReconciliationRenderer');
var ReconciliationAction = require('account.ReconciliationClientAction');
var ReconciliationModel = require('account.ReconciliationModel');
var core = require('web.core');
var _t = core._t;

ReconciliationAction.ManualAction.include({
    custom_events: _.extend({}, ReconciliationAction.ManualAction.prototype.custom_events || {}, {
        add_all_propositions: '_onAction',
    }),
});

ReconciliationModel.ManualModel.include({
    init: function () {
        this._super.apply(this, arguments);
        this.limitMoveLines = 9999;
    },

    addAllPropositions: function (handle, mv_line_ids) {
        var line = this.getLine(handle);
        _.each(mv_line_ids, (mv_line_id) => {
            var prop = _.clone(_.find(line['mv_lines_'+line.mode], {'id': mv_line_id}));
            if (prop && !prop.is_liquidity_line) {
                this._addProposition(line, prop);
            }
        });
        
        line.reconciliation_proposition = _.filter(line.reconciliation_proposition, function (prop) {return prop && !prop.invalid;});
        
        return this._computeLine(line);
    }
});

ReconciliationRenderer.ManualLineRenderer.include({
    events: _.extend({}, ReconciliationRenderer.ManualLineRenderer.prototype.events || {}, {
        'change input.filter_date_from': '_onFilterChange',
        'change input.filter_date_to': '_onFilterChange',
        'click .fa-search': '_onFilterChange',
        'keyup input.filter_date_from': function(e) { if(e.keyCode === 13) this._onFilterChange(e); },
        'keyup input.filter_date_to': function(e) { if(e.keyCode === 13) this._onFilterChange(e); },
        'click .btn_add_all_filtered': '_onAddAllFiltered',
    }),

    _onAddAllFiltered: function (event) {
        var self = this;
        var mv_line_ids = [];
        this.$('.match tbody .mv_line').each(function () {
            var id = $(this).data('line-id');
            if (id !== undefined && id !== null) {
                mv_line_ids.push(id);
            }
        });
        if (mv_line_ids.length > 0) {
            this.trigger_up('add_all_propositions', {'data': mv_line_ids});
        }
    },

    _onFilterChange: function (event) {
        var str = this.$('input.filter').val() || '';
        var from = this.$('input.filter_date_from').val() || '';
        var to = this.$('input.filter_date_to').val() || '';
        
        var combined = str;
        if (from || to) {
            combined += '|||' + from + '|||' + to;
        }
        
        this.trigger_up('change_filter', {'data': combined.trim()});
    },

    _render: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            // Restore date filter values if they exist
            var filter = self.state['filter_' + self.state.mode] || "";
            if (filter.indexOf('|||') !== -1) {
                var parts = filter.split('|||');
                var str = parts[0];
                var from = parts.length > 1 ? parts[1] : '';
                var to = parts.length > 2 ? parts[2] : '';
                
                self.$('input.filter').val(str);
                if (from) {
                    self.$('input.filter_date_from').val(from);
                }
                if (to) {
                    self.$('input.filter_date_to').val(to);
                }
            }
        });
    }
});

});
