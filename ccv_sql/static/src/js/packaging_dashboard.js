/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

const { Component, onWillStart, onMounted, useState, useRef } = owl;

export class PackagingDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null });

        this.chartPie = useRef("chartPie");
        this.chartBarAbs = useRef("chartBarAbs");
        this.chartLinePct = useRef("chartLinePct");
        this.chartTop10 = useRef("chartTop10");

        onWillStart(async () => {
            // Load Chart.js if not already loaded
            await loadJS("/web/static/lib/Chart/Chart.js");
            // Lấy data từ python model
            this.state.data = await this.orm.call("ccv.packaging.dashboard", "get_data", []);
        });

        onMounted(() => {
            if (this.state.data) {
                this.renderCharts();
            }
        });
    }

    renderCharts() {
        const data = this.state.data;
        const items = data.items_below_min;

        // 1. Chart Pie: Tỷ lệ an toàn vs thiếu hụt
        new Chart(this.chartPie.el, {
            type: 'pie',
            data: {
                labels: ['Bao Bì Thiếu Hụt', 'Bao Bì An Toàn'],
                datasets: [{
                    data: [data.below_min_count, data.safe_count],
                    backgroundColor: ['#dc3545', '#198754'],
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });

        if (items.length === 0) return; // Nếu không có sản phẩm thiếu hụt thì ngừng vẽ các biểu đồ dưới

        const labels = items.map(item => item.code);
        const absMissing = items.map(item => item.missing_qty);
        const pctMissing = items.map(item => item.missing_percent);

        // 2. Chart Bar: Số lượng thiếu hụt tuyệt đối
        const barChart = new Chart(this.chartBarAbs.el, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Số lượng thiếu',
                    data: absMissing,
                    backgroundColor: '#0d6efd',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                },
                onClick: (event, activeElements) => {
                    let elements = activeElements;
                    if (!elements || elements.length === 0) {
                        elements = barChart.getElementsAtEvent ? barChart.getElementsAtEvent(event) : [];
                    }
                    if (elements && elements.length > 0) {
                        const activeEl = elements[0];
                        const dataIndex = activeEl.index !== undefined ? activeEl.index : activeEl._index;
                        const item = items[dataIndex];
                        if (item && item.op_id) {
                            this.action.doAction({
                                type: 'ir.actions.act_window',
                                name: 'Chi tiết bao bì',
                                res_model: 'stock.warehouse.orderpoint',
                                view_mode: 'form',
                                views: [[false, 'form']],
                                res_id: item.op_id,
                                target: 'current',
                            });
                        }
                    }
                }
            }
        });

        // 3. Chart Line: Tỷ lệ % thiếu hụt
        new Chart(this.chartLinePct.el, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: '% Thiếu hụt',
                    data: pctMissing,
                    borderColor: '#fd7e14',
                    backgroundColor: 'rgba(253, 126, 20, 0.2)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { 
                        beginAtZero: true,
                        max: 100,
                        ticks: { callback: function(value) { return value + "%" } }
                    }
                }
            }
        });

        // 4. Chart PolarArea: Top 10 thiếu hụt nhiều nhất
        const top10Items = items.slice(0, 10);
        const top10Labels = top10Items.map(item => item.code);
        const top10Data = top10Items.map(item => item.missing_qty);

        // Generate some nice colors for Top 10
        const colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#E7E9ED', '#8AC249', '#FF5722', '#009688'
        ];

        new Chart(this.chartTop10.el, {
            type: 'polarArea',
            data: {
                labels: top10Labels,
                datasets: [{
                    data: top10Data,
                    backgroundColor: colors.slice(0, top10Data.length),
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right' }
                }
            }
        });
    }

    openMissingOrderpoints() {
        if (!this.state.data || !this.state.data.items_below_min.length) {
            return;
        }
        const opIds = this.state.data.items_below_min.map(item => item.op_id);
        
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Bao bì thiếu hụt',
            res_model: 'stock.warehouse.orderpoint',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: [['id', 'in', opIds]],
            target: 'current',
        });
    }

    openAllOrderpoints() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Tổng số lượng bao bì',
            res_model: 'stock.warehouse.orderpoint',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: [['product_id.default_code', '=like', 'BB.%']],
            target: 'current',
        });
    }

    openSafeOrderpoints() {
        const domain = [['product_id.default_code', '=like', 'BB.%']];
        if (this.state.data && this.state.data.items_below_min.length > 0) {
            const opIds = this.state.data.items_below_min.map(item => item.op_id);
            domain.push(['id', 'not in', opIds]);
        }
        
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Bao bì an toàn',
            res_model: 'stock.warehouse.orderpoint',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            target: 'current',
        });
    }
}

PackagingDashboard.template = "ccv_sql.PackagingDashboard";
registry.category("actions").add("ccv_packaging_dashboard", PackagingDashboard);
