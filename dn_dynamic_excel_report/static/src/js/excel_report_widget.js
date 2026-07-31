odoo.define('dn_dynamic_excel_report.ExcelReportWidget', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var Dialog = require('web.Dialog');

    var _t = core._t;

    /**
     * Excel Report Widget
     * Handles Excel report generation and download
     */
    var ExcelReportWidget = Widget.extend({
        template: 'dn_dynamic_excel_report.ExcelReportTemplate',

        events: {
            'click .o_excel_report_download': '_onDownloadClick',
            'click .o_excel_report_preview': '_onPreviewClick',
            'change .o_excel_report_select': '_onReportSelectChange',
        },

        /**
         * @override
         */
        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.reportId = options.reportId || false;
            this.modelName = options.modelName || false;
            this.recordIds = options.recordIds || [];
            this.availableReports = options.availableReports || [];
        },

        /**
         * @override
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._loadAvailableReports();
            });
        },

        /**
         * Load available reports for the current model
         */
        _loadAvailableReports: function () {
            var self = this;
            this._rpc({
                model: 'excel.report',
                method: 'search_read',
                args: [[
                    ['model_name', '=', this.modelName],
                    ['active', '=', true],
                    ['state', '=', 'published'],
                ], ['id', 'name', 'code']],
            }).then(function (reports) {
                self.availableReports = reports;
                self._renderReportSelect();
            });
        },

        /**
         * Render report selection dropdown
         */
        _renderReportSelect: function () {
            var self = this;
            var $select = this.$('.o_excel_report_select');
            $select.empty();
            
            // Add default option
            $select.append($('<option>').val('').text(_t('Select a report')));
            
            // Add available reports
            this.availableReports.forEach(function (report) {
                $select.append($('<option>')
                    .val(report.id)
                    .text(report.name));
            });
            
            // Select current report if set
            if (this.reportId) {
                $select.val(this.reportId);
            }
        },

        /**
         * Handle report selection change
         */
        _onReportSelectChange: function (ev) {
            this.reportId = $(ev.currentTarget).val();
            this.$('.o_excel_report_download').prop('disabled', !this.reportId);
            this.$('.o_excel_report_preview').prop('disabled', !this.reportId);
        },

        /**
         * Handle download button click
         */
        _onDownloadClick: function (ev) {
            ev.preventDefault();
            if (!this.reportId) {
                this.do_warn(_t('Warning'), _t('Please select a report first.'));
                return;
            }
            this._downloadReport();
        },

        /**
         * Handle preview button click
         */
        _onPreviewClick: function (ev) {
            ev.preventDefault();
            if (!this.reportId) {
                this.do_warn(_t('Warning'), _t('Please select a report first.'));
                return;
            }
            this._previewReport();
        },

        /**
         * Download Excel report
         */
        _downloadReport: function () {
            var url = '/excel/report/export/' + this.modelName + '/' + this.reportId;
            var params = {
                record_ids: this.recordIds.join(','),
            };
            
            // Add timestamp to prevent caching
            var separator = url.indexOf('?') === -1 ? '?' : '&';
            url += separator + 'timestamp=' + new Date().getTime();
            
            // Build query string
            var queryString = $.param(params);
            if (queryString) {
                url += '&' + queryString;
            }
            
            // Download file
            window.location.href = url;
        },

        /**
         * Preview Excel report
         */
        _previewReport: function () {
            var url = '/excel/report/preview/' + this.reportId;
            
            // Add timestamp to prevent caching
            var separator = url.indexOf('?') === -1 ? '?' : '&';
            url += separator + 'timestamp=' + new Date().getTime();
            
            // Download preview file
            window.location.href = url;
        },
    });

    /**
     * Excel Report Dialog
     * Dialog for selecting and generating Excel reports
     */
    var ExcelReportDialog = Dialog.extend({
        template: 'dn_dynamic_excel_report.ExcelReportDialogTemplate',
        
        init: function (parent, options) {
            this._super(parent, _.extend({}, options, {
                title: options.title || _t('Generate Excel Report'),
                size: 'medium',
            }));
            this.modelName = options.modelName;
            this.recordIds = options.recordIds || [];
        },

        /**
         * @override
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.excelWidget = new ExcelReportWidget(self, {
                    modelName: self.modelName,
                    recordIds: self.recordIds,
                });
                self.excelWidget.appendTo(self.$('.o_excel_report_widget_container'));
            });
        },
    });

    // Register widget
    core.action_registry.add('excel_report_widget', ExcelReportWidget);

    return {
        ExcelReportWidget: ExcelReportWidget,
        ExcelReportDialog: ExcelReportDialog,
    };
});