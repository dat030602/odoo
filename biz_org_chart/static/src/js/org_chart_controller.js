odoo.define('biz_org_chart.OrgChartController', function(require) {
    'use strict';

    var AbstractController = require('web.AbstractController');
    var OrgChartController = AbstractController.extend({

        /**
         * @override
         * @param {OdooEvent} ev
         */
        _onOpenRecord: function (ev) {
            ev.stopPropagation();
            this.trigger_up('switch_view', {
                view_type: 'form',
                res_id: ev.data.id,
                mode: ev.data.mode || 'readonly',
                model: this.modelName,
            });
        },
    });

    return OrgChartController;

});