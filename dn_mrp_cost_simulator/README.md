# MRP Costing Simulation & Version Manager (`dn_mrp_cost_simulator`)

**Odoo 19 Module** for Manufacturing Cost Simulation, Sandbox Price Modeling, Multi-Level BOM Traversal, Pre-Costing Data Audits, and Post-Costing Variance Reporting.

---

## Key Highlights & Capabilities

### 1. Isolated Physical Sandbox (`mrp.bom.simulation`)
- **Independent Data Layer**: Uses physical models (`mrp.bom.simulation`, `mrp.bom.simulation.line`, `mrp.bom.simulation.operation`, `mrp.bom.simulation.byproduct`) completely decoupled from `account.move` and `stock.valuation.layer` (SVL).
- **Hypothetical Price Injection**: Overrides material costs, scrap rates, and work center hourly wages/power costs without altering live product catalog or routing templates.
- **Fast In-Memory Multi-Level Traversal**: Avoids ORM N+1 recursive loops through batch dictionary processing, handling sub-assemblies and Kit/Phantom BOMs natively.
- **By-Product & Yield Deduction**: Incorporates `cost_share` formulas to accurately allocate cost to by-products and derive the net unit cost of the parent product.
- **Multi-Currency Analysis**: Translates base manufacturing costs to any target currency using dynamic exchange rate simulation.

### 2. Version Control & Snapshot Revisions
- **Snapshot Branching**: Create revisions (V1, V2, V3...) to compare competing what-if scenarios (e.g. "Raw Material Hike +10%", "New Assembly Line Efficiency").
- **Audit Workflow**: `Draft` ➔ `Calculated` ➔ `Approved` ➔ `Applied`.
- **Production Update (`action_apply_simulation`)**: Updates the product's live standard cost (`standard_price`) with automated chatter tracking and audit logging.

### 3. Pre-Costing Data Validation Suite
Helps cost accountants detect data discrepancies before closing or running production calculations:
- **BOM Cost Exceptions Audit**: Instant scan for components with zero cost (`0.00`), work centers with zero hourly rate, empty BOMs, or invalid byproduct cost shares (>100%).
- **Material Consumption Variance**: Analyzes standard planned BOM consumption against actual stock consumption on Manufacturing Orders.
- **WIP (Work In Progress) Valuation Snapshot**: Real-time snapshot of uncompleted MOs, tracking raw material issued value minus finished goods received value.
- **Labor & Machine Timesheet Audit**: Audits work orders with zero recorded duration or unconfigured work center cost rates.

### 4. Post-Costing Variance Analysis
High-performance PostgreSQL SQL Views (`_auto = False`) with Pivot & List views:
- **Cost Variance Matrix (Planned vs Actual)**: Deconstructs manufacturing costs into Direct Materials, Direct Labor, and Total Cost, highlighting cost overruns or savings.
- **Gross Margin by Manufacturing Order**: Links Sales Orders (`sale.order`) directly with Manufacturing Orders (`mrp.production`) to calculate actual gross profit and gross margin %.

---

## Technical Architecture

| Component | Technical Model / View | Description |
|---|---|---|
| Simulation Header | `mrp.bom.simulation` | Scenario metadata, currency, totals, state lifecycle |
| Component Breakdown | `mrp.bom.simulation.line` | Materials, levels, scrap %, injected prices, subtotals |
| Routing Breakdown | `mrp.bom.simulation.operation` | Operations, work centers, simulated durations and rates |
| By-Product Allocation | `mrp.bom.simulation.byproduct` | By-products and `cost_share` deductions |
| BOM Exception Audit | `mrp.cost.bom.exception` | Automated rule checker for active BOM sanity |
| Consumption Variance | `mrp.cost.consumption.variance` | SQL View: Standard vs Actual material consumption |
| WIP Snapshot | `mrp.cost.wip.snapshot` | SQL View: Work-in-Progress balance per open MO |
| WO Audit | `mrp.cost.workcenter.audit` | SQL View: Work order duration & rate discrepancies |
| Cost Variance Matrix | `mrp.cost.variance.matrix` | SQL View: Planned vs Actual Material & Labor |
| MO Gross Margin | `mrp.cost.gross.margin` | SQL View: SO revenue vs MO actual production cost |

---

## Installation & Testing

The module requires:
- `mrp`
- `stock_account`
- `mrp_account`
- `sale`

Run tests via the Odoo CLI:
```bash
/opt/venv312/bin/python3.12 /opt/odoo19/odoo-bin -c /opt/odoo19.conf -d odoo19 -u dn_mrp_cost_simulator --test-enable --test-tags /dn_mrp_cost_simulator --stop-after-init
```
