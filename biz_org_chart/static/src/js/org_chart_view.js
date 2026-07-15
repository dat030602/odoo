odoo.define('biz_org_chart.OrgChartView', function(require) {
    'use strict';

    var core = require('web.core');
    var AbstractView = require('web.AbstractView');

    var OrgChartModel = require('biz_org_chart.OrgChartModel');
    var OrgChartRenderer = require('biz_org_chart.OrgChartRenderer');
    var OrgChartController = require('biz_org_chart.OrgChartController');

    var viewRegistry = require('web.view_registry');
    var _lt = core._lt;

    var OrgChartView = AbstractView.extend({
        display_name: _lt('Org Chart'),
        icon: 'fa-sitemap',
        config: _.extend({}, AbstractView.prototype.config, {
            Model: OrgChartModel,
            Controller: OrgChartController,
            Renderer: OrgChartRenderer,
        }),
        cssLibs: [
            '/biz_org_chart/static/lib/orgchart/jquery.orgchart.css',
        ],
        jsLibs: [
            '/biz_org_chart/static/lib/html2canvas/html2canvas.min.js',
            '/biz_org_chart/static/lib/orgchart/jquery.orgchart.js',
        ],
        viewType: 'org',
        groupable: false,
        withSearchPanel: false,

        init: function() {
            this._super.apply(this, arguments);
        },
    });

    viewRegistry.add('org', OrgChartView);

    return OrgChartView;

});