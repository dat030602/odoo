odoo.define('biz_org_chart.OrgChartRenderer', function(require) {
    'use strict';

    var core = require('web.core');
    var AbstractRenderer = require('web.AbstractRenderer');
    var _lt = core._lt;


    var OrgChartRenderer = AbstractRenderer.extend({
        className: "o_org_chart",

        events: {
            "click .node-action": "_onNodeActionClicked",
            "click .objective_name, .department, .bottom_block": "_onNodeClicked",
        },
        
        /**
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onNodeActionClicked: function (ev) {
        	ev.preventDefault();
        	var $action = $(ev.currentTarget);
        	var record_id = $action.data('record-id');
        	var type = $action.data('type');
        	this.trigger_up('open_record', {id: record_id, mode: type });
        },
        
        /**
        *
        * @private
        * @param {MouseEvent} ev
        */
       _onNodeClicked: function (ev) {
       	ev.preventDefault();
       	var node_menu = $(ev.currentTarget).closest('.node_content').find('.node_menu');
       	var record_id = node_menu.data('record-id');
       	if (record_id) {
       		this.trigger_up('open_record', {id: record_id});
       	}
       },
     
        /**
        * @override
        */
        _render: function() {
            this.$el.empty();
            this.$el.append(
                $('<div id="to_org_chart"/>')
            );
            this._renderOrgChart();
            return this._super.apply(this, arguments);
        },

        /**
        * render org chart using orgchart library
        * @private
        */
        _renderOrgChart: function() {
            var self = this;
            var nodeRefs = [];
            var yearNodes = [];
            var nodeTryTimes = {};
            // create a clone of records
            var records = this.state.records.slice();
            while (records.length > 0) {
                // get first item in list
                var record = records.shift();
                // create default node
                var node = {
                    'type': 'record',
                    'name': record.name,
                    'record': record,
                    'children': []
                }
                // add new year node if not exist
                var yearNode = yearNodes.find(n => n.year == record.year)
                if (yearNode == undefined) {
                    yearNode = {
                        'type': 'year',
                        'name': _lt('Year ') + record.year,
                        'year': record.year,
                        'children': []
                    };
                    yearNodes.push(yearNode);
                }
                // check for where to add current node
                if (!record.parent_id) {
                    // if this node set quarter
                    if (record.quarter) {
                        // then it should be child of quarter node of this year
                        var foundQNode = false;
                        yearNode.children.forEach(quarterNode => {
                            // find correct quarter node and set it as children
                            if ('quarter' in quarterNode && quarterNode.quarter == record.quarter) {
                                quarterNode.children.push(node);
                                foundQNode = true;
                            }
                        });
                        // create new quarter node if it is not exist
                        if (!foundQNode) {
                            yearNode.children.push({
                                'type': 'quarter',
                                'name': _lt('Quarter ') + (parseInt(record.quarter) + 1),
                                'quarter': record.quarter,
                                'children': [node]
                            });
                        }
                    } else {
                        // if it is not set quarter then it should be objective of year
                        // and directly added to year
                        yearNode.children.push(node)
                    }
                } else {
                    // if record have parent then we need to find parent in list
                    var parent_node = nodeRefs.find(n => n.record.id == record.parent_id[0])
                    if (parent_node != undefined) {
                        // add this node to it's parent node
                        parent_node.children.push(node);
                    } else {
                        // in case of parent node not found, there is maybe parent node is not processed in list
                        // so we just push this record back to list
                        if (record.id in nodeTryTimes) {
                            // we continue here as we do not want push it again to nodeRefs
                            // and also we avoid it push it again to records
                            // TODO: what to do with this record ?
                            console.warn(`Record: ${record} parent is not found. What should we do with this record?`)
                            continue;
                        } else {
                            records.push(record);
                            nodeTryTimes[record.id] = 1;
                        }
                    }
                }
                // store in nodeRefs for quick reference later when we find for parent
                nodeRefs.push(node)
            }
            // only continue to generate chart in case we have data
            if (yearNodes.length > 0) {
                // create virtual company node
                var data = {
                    'type': 'company',
                    'name': nodeRefs[0].record.company_id[1],
                    'children': yearNodes
                };

                var nodeTemplate = data => { return this._getNodeTemplate(data); };

                this._initOrgChat(data, nodeTemplate);
            }
        },

        /**
        * initialize org chart
        * 
        * @todo move this to qweb template and use qweb.render instead
        * @private
        */
        _initOrgChat: function(data, nodeTemplate) {
            this.$el.find("#to_org_chart").orgchart({
                'data': data,
                'pan': true,
                'zoom': true,
                'chartClass': 'to_org_chart',
                'toggleSiblingsResp': false,
                'nodeTemplate': nodeTemplate,
                'initCompleted': () => {
                    $('[data-toggle="popover"]').popover();
                }
            });
        },

        /**
        * get node template for rendering
        * 
        * @todo move this to qweb template and use qweb.render instead
        * @private
        */
        _getNodeTemplate: function(node) {
            var nodeClass = '';
            var nodeMenu = '';
            if (node.type == 'company') {
                nodeClass = 'company_node';
            } else if (node.type == 'year') {
                nodeClass = 'year_node';
            } else if (node.type == 'quarter') {
                nodeClass = 'quarter_node';
            } else {
                nodeMenu = `
                <div class="node_menu dropdown" data-record-id="${node.record.id}">
                    <a class="" type="button" id="node_menu_${node.record.id}" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                        <i class="fa fa-ellipsis-v"></i>
                    </a>
                    <div class="dropdown-menu" aria-labelledby="node_menu_${node.record.id}">
                        <a class="dropdown-item node-action" data-type="edit" data-record-id="${node.record.id}"><i class="fa fa-pencil"></i>Edit</a>
                    </div>
                </div>
            `;
            }

            var html = `
        <div class="node_content ${nodeClass}">
            ${nodeMenu}
            <div class='objective_name'>${node.name}</div>
        `;
            if (node.type == 'record') {
                var progress = Math.max(0, Math.min(100, Math.floor(node.record.points * 100)))
                var progressColor = 'bg-danger';
                if (node.record.result == 'successful') {
                    progressColor = 'bg-success';
                }
                if (node.record.mode == 'department') {
                    html += `
                     <div class='department'>${node.record.department_id[1]}</div>
                `;
                } else if (node.record.mode == 'employee') {
                    html += `
                     <div class='department'>${node.record.user_id[1]}</div>
                `;
                } else if (node.record.mode == 'company') {
                    html += `
                     <div class='department'>${_lt('Company Objective')}</div>
                `;
                }

                html += `
                <div class='bottom_block'>
                    <div class='owner'>
                        <img class="rounded-circle" src="/web/image/res.users/${node.record.user_id[0]}/image_128"" alt="User">
                    </div>
                    <div class='points'>${progress}%</div>
                </div>
                <div class="progress">
                    <div class="progress-bar ${progressColor}" role="progressbar" style="width: ${progress}%"></div>
                </div>
            `;
            }

            // finally close div
            html += `
        </div>
        `;
            return html;
        },
    });



    return OrgChartRenderer;

});