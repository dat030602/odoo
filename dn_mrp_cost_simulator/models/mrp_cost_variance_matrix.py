from odoo import fields, models, tools


class MrpCostVarianceMatrix(models.Model):
    _name = 'mrp.cost.variance.matrix'
    _description = 'Manufacturing Cost Variance Matrix (Planned vs Actual)'
    _auto = False
    _order = 'date_done desc, total_variance desc'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', readonly=True)
    product_id = fields.Many2one('product.product', string='Finished Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials', readonly=True)
    product_qty = fields.Float(string='Planned Qty', readonly=True)
    qty_produced = fields.Float(string='Actual Produced Qty', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    date_done = fields.Datetime(string='Completion Date', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='MO Status', readonly=True)

    # Cost Breakdowns
    planned_material_cost = fields.Monetary(string='Planned Material Cost', currency_field='currency_id', readonly=True)
    actual_material_cost = fields.Monetary(string='Actual Material Cost', currency_field='currency_id', readonly=True)
    material_variance = fields.Monetary(string='Material Variance', currency_field='currency_id', readonly=True)

    planned_labor_cost = fields.Monetary(string='Planned Labor Cost', currency_field='currency_id', readonly=True)
    actual_labor_cost = fields.Monetary(string='Actual Labor Cost', currency_field='currency_id', readonly=True)
    labor_variance = fields.Monetary(string='Labor Variance', currency_field='currency_id', readonly=True)

    total_planned_cost = fields.Monetary(string='Total Planned Cost', currency_field='currency_id', readonly=True)
    total_actual_cost = fields.Monetary(string='Total Actual Cost', currency_field='currency_id', readonly=True)
    total_variance = fields.Monetary(string='Total Cost Variance', currency_field='currency_id', readonly=True)
    variance_pct = fields.Float(string='Total Variance %', readonly=True)

    planned_unit_cost = fields.Monetary(string='Planned Unit Cost', currency_field='currency_id', readonly=True)
    actual_unit_cost = fields.Monetary(string='Actual Unit Cost', currency_field='currency_id', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH material_summary AS (
                    SELECT
                        sm.raw_material_production_id AS production_id,
                        SUM(
                            COALESCE(sm.product_uom_qty, 0.0) *
                            COALESCE(
                                (pp_raw.standard_price->>mp_raw.company_id::text)::numeric,
                                (pp_raw.standard_price->>'1')::numeric,
                                sm.price_unit,
                                0.0
                            )
                        ) AS planned_mat_cost,
                        SUM(
                            COALESCE(
                                NULLIF(ABS(svl.total_val), 0),
                                sm.quantity * COALESCE(
                                    (pp_raw.standard_price->>mp_raw.company_id::text)::numeric,
                                    (pp_raw.standard_price->>'1')::numeric,
                                    sm.price_unit,
                                    0.0
                                )
                            )
                        ) AS actual_mat_cost
                    FROM stock_move sm
                    JOIN mrp_production mp_raw ON sm.raw_material_production_id = mp_raw.id
                    JOIN product_product pp_raw ON sm.product_id = pp_raw.id
                    LEFT JOIN (
                        SELECT stock_move_id, SUM(value) AS total_val
                        FROM stock_valuation_layer
                        GROUP BY stock_move_id
                    ) svl ON svl.stock_move_id = sm.id
                    WHERE sm.raw_material_production_id IS NOT NULL AND sm.state != 'cancel'
                    GROUP BY sm.raw_material_production_id
                ),
                labor_summary AS (
                    SELECT
                        mp.id AS production_id,
                        COALESCE(
                            wo_summary.planned_lab_cost,
                            (COALESCE(bom_op.unit_op_cost, 0.0) * mp.product_qty),
                            0.0
                        ) AS planned_lab_cost,
                        COALESCE(wo_summary.actual_lab_cost, 0.0) AS actual_lab_cost
                    FROM mrp_production mp
                    LEFT JOIN (
                        SELECT
                            wo.production_id,
                            SUM((COALESCE(wo.duration_expected, 0.0) / 60.0) * COALESCE(wc.costs_hour, 0.0)) AS planned_lab_cost,
                            SUM((COALESCE(wo.duration, 0.0) / 60.0) * COALESCE(wc.costs_hour, 0.0)) AS actual_lab_cost
                        FROM mrp_workorder wo
                        JOIN mrp_workcenter wc ON wo.workcenter_id = wc.id
                        WHERE wo.state != 'cancel'
                        GROUP BY wo.production_id
                    ) wo_summary ON wo_summary.production_id = mp.id
                    LEFT JOIN (
                        SELECT
                            op.bom_id,
                            SUM((COALESCE(op.time_cycle_manual, 0.0) / 60.0) * COALESCE(wc.costs_hour, 0.0)) AS unit_op_cost
                        FROM mrp_routing_workcenter op
                        JOIN mrp_workcenter wc ON op.workcenter_id = wc.id
                        GROUP BY op.bom_id
                    ) bom_op ON bom_op.bom_id = mp.bom_id
                )
                SELECT
                    mp.id AS id,
                    mp.id AS production_id,
                    mp.product_id AS product_id,
                    pp.product_tmpl_id AS product_tmpl_id,
                    pt.categ_id AS categ_id,
                    mp.bom_id AS bom_id,
                    mp.product_qty AS product_qty,
                    COALESCE(mp.qty_producing, mp.product_qty, 0.0) AS qty_produced,
                    mp.company_id AS company_id,
                    rc.currency_id AS currency_id,
                    mp.date_finished AS date_done,
                    mp.state AS state,

                    -- Materials
                    COALESCE(ms.planned_mat_cost, 0.0) AS planned_material_cost,
                    COALESCE(ms.actual_mat_cost, 0.0) AS actual_material_cost,
                    (COALESCE(ms.actual_mat_cost, 0.0) - COALESCE(ms.planned_mat_cost, 0.0)) AS material_variance,

                    -- Labor
                    COALESCE(ls.planned_lab_cost, 0.0) AS planned_labor_cost,
                    COALESCE(ls.actual_lab_cost, 0.0) AS actual_labor_cost,
                    (COALESCE(ls.actual_lab_cost, 0.0) - COALESCE(ls.planned_lab_cost, 0.0)) AS labor_variance,

                    -- Totals
                    (COALESCE(ms.planned_mat_cost, 0.0) + COALESCE(ls.planned_lab_cost, 0.0)) AS total_planned_cost,
                    (COALESCE(ms.actual_mat_cost, 0.0) + COALESCE(ls.actual_lab_cost, 0.0)) AS total_actual_cost,
                    ((COALESCE(ms.actual_mat_cost, 0.0) + COALESCE(ls.actual_lab_cost, 0.0)) -
                     (COALESCE(ms.planned_mat_cost, 0.0) + COALESCE(ls.planned_lab_cost, 0.0))) AS total_variance,

                    -- Variance %
                    CASE
                        WHEN (COALESCE(ms.planned_mat_cost, 0.0) + COALESCE(ls.planned_lab_cost, 0.0)) > 0 THEN
                            (((COALESCE(ms.actual_mat_cost, 0.0) + COALESCE(ls.actual_lab_cost, 0.0)) -
                              (COALESCE(ms.planned_mat_cost, 0.0) + COALESCE(ls.planned_lab_cost, 0.0))) /
                             (COALESCE(ms.planned_mat_cost, 0.0) + COALESCE(ls.planned_lab_cost, 0.0))) * 100.0
                        ELSE 0.0
                    END AS variance_pct,

                    -- Unit costs
                    CASE
                        WHEN mp.product_qty > 0 THEN
                            (COALESCE(ms.planned_mat_cost, 0.0) + COALESCE(ls.planned_lab_cost, 0.0)) / mp.product_qty
                        ELSE 0.0
                    END AS planned_unit_cost,

                    CASE
                        WHEN COALESCE(mp.qty_producing, mp.product_qty, 0.0) > 0 THEN
                            (COALESCE(ms.actual_mat_cost, 0.0) + COALESCE(ls.actual_lab_cost, 0.0)) / COALESCE(mp.qty_producing, mp.product_qty, 1.0)
                        ELSE 0.0
                    END AS actual_unit_cost

                FROM mrp_production mp
                JOIN product_product pp ON mp.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN res_company rc ON mp.company_id = rc.id
                LEFT JOIN material_summary ms ON ms.production_id = mp.id
                LEFT JOIN labor_summary ls ON ls.production_id = mp.id
                WHERE mp.state IN ('progress', 'to_close', 'done')
            )
        """)


class MrpCostGrossMargin(models.Model):
    _name = 'mrp.cost.gross.margin'
    _description = 'Gross Margin by Manufacturing Order'
    _auto = False
    _order = 'gross_margin_pct desc'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True)
    sale_line_id = fields.Many2one('sale.order.line', string='Sales Order Line', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    qty_produced = fields.Float(string='Qty Produced', readonly=True)
    sale_revenue = fields.Monetary(string='Sale Revenue', currency_field='currency_id', readonly=True)
    actual_mfg_cost = fields.Monetary(string='Actual Manufacturing Cost', currency_field='currency_id', readonly=True)
    gross_profit = fields.Monetary(string='Gross Profit', currency_field='currency_id', readonly=True)
    gross_margin_pct = fields.Float(string='Gross Margin %', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date_done = fields.Datetime(string='Date Completed', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH actual_costs AS (
                    SELECT
                        production_id,
                        total_actual_cost
                    FROM mrp_cost_variance_matrix
                )
                SELECT
                    mp.id AS id,
                    mp.id AS production_id,
                    so.id AS sale_order_id,
                    sol.id AS sale_line_id,
                    so.partner_id AS partner_id,
                    mp.product_id AS product_id,
                    COALESCE(mp.qty_producing, mp.product_qty, 0.0) AS qty_produced,
                    COALESCE(sol.price_subtotal, pt.list_price * COALESCE(mp.qty_producing, mp.product_qty, 0.0)) AS sale_revenue,
                    COALESCE(ac.total_actual_cost, 0.0) AS actual_mfg_cost,
                    (COALESCE(sol.price_subtotal, pt.list_price * COALESCE(mp.qty_producing, mp.product_qty, 0.0)) - COALESCE(ac.total_actual_cost, 0.0)) AS gross_profit,
                    CASE
                        WHEN COALESCE(sol.price_subtotal, pt.list_price * COALESCE(mp.qty_producing, mp.product_qty, 0.0)) > 0 THEN
                            (((COALESCE(sol.price_subtotal, pt.list_price * COALESCE(mp.qty_producing, mp.product_qty, 0.0)) - COALESCE(ac.total_actual_cost, 0.0)) /
                              COALESCE(sol.price_subtotal, pt.list_price * COALESCE(mp.qty_producing, mp.product_qty, 0.0))) * 100.0)
                        ELSE 0.0
                    END AS gross_margin_pct,
                    rc.currency_id AS currency_id,
                    mp.company_id AS company_id,
                    mp.date_finished AS date_done
                FROM mrp_production mp
                JOIN product_product pp ON mp.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN sale_order_line sol ON mp.sale_line_id = sol.id
                LEFT JOIN sale_order so ON sol.order_id = so.id
                JOIN res_company rc ON mp.company_id = rc.id
                LEFT JOIN actual_costs ac ON ac.production_id = mp.id
                WHERE mp.state = 'done'
            )
        """)
