odoo.define('biz_org_chart.test_utils_create', function (require) {
"use strict";

/**
 * Create Test Utils
 *
 * This module defines various utility functions to help creating mock widgets
 *
 * Note that all methods defined in this module are exported in the main
 * testUtils file.
 */
var concurrency = require('web.concurrency');
var testUtilsCreate = require('web.test_utils_create');


/**
 * Similar as createView, but specific for org chart views. Some org chart
 * tests need to trigger positional clicks on the DOM produced by forg chart.
 * Those tests must use this helper with option positionalClicks set to true.
 *
 * @param {Object} params see @createView
 * @param {Object} [options]
 * @param {boolean} [options.positionalClicks=false]
 * @returns {Promise<CalendarController>}
 */
async function createOrgChartView(params, options) {
    var org_chart = await testUtilsCreate.createView(params);
    if (!options || !options.positionalClicks) {
        return org_chart;
    }
    var $view = $('#qunit-fixture').contents();
    $view.prependTo('body');
    var destroy = org_chart.destroy;
    org_chart.destroy = function () {
        $view.remove();
        destroy();
    };
    await concurrency.delay(0);
    return org_chart;
}

testUtilsCreate.createOrgChartView = createOrgChartView;
return testUtilsCreate;

});
