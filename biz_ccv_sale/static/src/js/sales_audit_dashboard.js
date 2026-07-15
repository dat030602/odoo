/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class SalesAuditDashboard extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        
        this.state = useState({
            date_from: "",
            date_to: "",
            data: {
                overview: {},
                warehouse_alerts: {},
                operations: {}
            }
        });

        onWillStart(async () => {
            await this._fetchData();
        });
    }

    async _fetchData() {
        const filters = {
            date_from: this.state.date_from,
            date_to: this.state.date_to,
        };
        const result = await this.rpc("/web/dataset/call_kw/sale.audit.dashboard/get_dashboard_data", {
            model: "sale.audit.dashboard",
            method: "get_dashboard_data",
            args: [filters],
            kwargs: {},
        });
        if (result) {
            this.state.data = result;
        }
    }

    _formatCurrency(value) {
        if (!value) return "0 ₫";
        return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
    }

    _openListView(filterType) {
        let domain = [];
        if (this.state.date_from) domain.push(["date_order", ">=", this.state.date_from]);
        if (this.state.date_to) domain.push(["date_order", "<=", this.state.date_to]);

        // Basic domain routing based on card clicked
        if (filterType === 'total_orders' || filterType === 'total_ordered_amount') {
            // Keep default domain
        } else if (filterType === 'to_deliver') {
            domain.push(["invoice_status", "!=", "invoiced"], ["state", "in", ["sale", "done"]]); // Simplified
        } else if (filterType === 'to_invoice') {
            domain.push(["invoice_status", "=", "to invoice"]);
        } else if (filterType === 'qty_delivered_zero') {
            // Can be complex to filter purely by domain if picking is required, 
            // In a real app we might return a list of IDs from backend for complex filters.
            // But this will open a standard view for now.
        }

        this.action.doAction({
            name: "Chi tiết Đơn hàng",
            type: "ir.actions.act_window",
            res_model: "sale.order",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }
}

SalesAuditDashboard.template = "ccv_sale.SalesAuditDashboard";

registry.category("actions").add("sales_audit_dashboard", SalesAuditDashboard);
