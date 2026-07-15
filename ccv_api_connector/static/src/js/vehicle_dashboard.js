/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, onMounted, onWillUnmount } from "@odoo/owl";

export class VehicleDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            tick: 0,
            data: {
                dang_ky: [],
                dang_cho: [],
                xuat_nhap: [],
                cho_ra: [],
                hoan_thanh: [],
                summary: {}
            }
        });

        onWillStart(async () => {
            await this.loadData();
        });

        onMounted(() => {
            this.pollingInterval = setInterval(() => {
                this.loadData();
            }, 20000); // 20 seconds

            this.tickInterval = setInterval(() => {
                this.state.tick++;
            }, 8000); // 8 seconds
        });

        onWillUnmount(() => {
            if (this.pollingInterval) {
                clearInterval(this.pollingInterval);
            }
            if (this.tickInterval) {
                clearInterval(this.tickInterval);
            }
        });
    }

    async loadData() {
        const data = await this.orm.call(
            "sale.vehicle.in.out.line",
            "get_vehicle_dashboard_data",
            []
        );
        console.log("Dashboard Data Loaded:", data);
        Object.assign(this.state.data, data);
    }
    
    getDisplayedLines(category) {
        const arr = this.state.data[category] || [];
        const len = arr.length;
        if (len <= 3) return arr;
        
        const tick = this.state.tick || 0;
        const startIdx = (tick * 3) % len;
        
        const displayed = [];
        for (let i = 0; i < 3; i++) {
            displayed.push(arr[(startIdx + i) % len]);
        }
        return displayed;
    }

    // Helper function to get row span for the category header
    getRowSpan(category) {
        const len = this.getDisplayedLines(category).length;
        return len > 0 ? len : 1;
    }
}

VehicleDashboard.template = "ccv_api_connector.VehicleDashboard";

registry.category("actions").add("ccv_vehicle_dashboard", VehicleDashboard);
