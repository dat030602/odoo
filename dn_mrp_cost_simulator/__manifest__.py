{
    'name': 'MRP Costing Simulation & Version Manager',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'Simulate, Version, and Analyze Multi-level BOM Costs, Location Valuation, and Manufacturing Cost Variances',
    'description': """
MRP Costing Simulation & Version Manager (dn_mrp_cost_simulator)
================================================================
Comprehensive Cost Simulation, Sandbox Analysis, and Variance Reporting for Odoo Manufacturing.

Key Features:
-------------
1. **BOM Cost Simulation Sandbox**:
   - Physical sandbox models (`mrp.bom.simulation`) isolated from live accounting.
   - Fast recursive multi-level BOM decomposition (avoiding ORM N+1 bottlenecks).
   - Support for Sub-assemblies and Phantom BOMs (Kits).
   - Direct material breakdown with Scrap/Yield % adjustment.
   - Direct labor breakdown with Work Center hourly rate overrides and cycle times.
   - By-product cost allocations (`cost_share`).
   - Hypothetical price injection for materials, labor rates, and overhead.
   - Multi-currency rate simulation.

2. **Simulation Version Control**:
   - Snapshot simulations into version trees (V1, V2, V3...).
   - Workflow: Draft -> Calculated -> Approved -> Applied.
   - One-click application to real BOM or standard product cost.

3. **Pre-Costing Validation Suite**:
   - BOM Cost Exception Audit (detecting zero-cost components, missing work center rates).
   - Material Consumption Variance (Standard vs. Actual on MOs).
   - WIP (Work In Progress) Valuation Snapshot for open MOs.
   - Work Order Productivity & Timesheet Audit (zero-duration completed operations).

4. **Post-Costing Analysis Suite**:
   - Cost Variance Matrix (Planned vs. Actual Material, Labor, and Overhead).
   - High-performance PostgreSQL SQL Views (`_auto = False`) with Pivot and Graph analysis.
   - Gross Margin Analysis connecting Sales Orders to Manufacturing Orders.
    """,
    'author': 'Dat Nguyen',
    'depends': [
        'mrp',
        'stock_account',
        'mrp_account',
        'sale',
    ],
    'data': [
        'security/mrp_cost_simulator_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/mrp_bom_simulation_views.xml',
        'views/mrp_cost_pre_validation_views.xml',
        'views/mrp_cost_variance_report_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
