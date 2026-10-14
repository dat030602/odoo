from odoo import api, fields, models, tools, _


class MrpCostBomException(models.Model):
    _name = 'mrp.cost.bom.exception'
    _description = 'BOM Cost Exception Audit'
    _order = 'severity desc, id desc'

    name = fields.Char(string='Issue Description', required=True)
    severity = fields.Selection([
        ('warning', 'Warning'),
        ('critical', 'Critical')
    ], string='Severity', default='warning', required=True)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials', required=True)
    product_tmpl_id = fields.Many2one('product.template', related='bom_id.product_tmpl_id', store=True)
    product_id = fields.Many2one('product.product', string='Problematic Product/Component')
    workcenter_id = fields.Many2one('mrp.workcenter', string='Problematic Work Center')
    exception_type = fields.Selection([
        ('zero_material_cost', 'Component with Zero Cost (0.00)'),
        ('zero_workcenter_rate', 'Work Center with Zero Hourly Rate (0.00)'),
        ('empty_bom', 'BOM without Components'),
        ('invalid_cost_share', 'Byproduct Cost Share Invalid (>100% or <0%)'),
    ], string='Exception Category', required=True)
    suggested_action = fields.Char(string='Suggested Remediation')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.model
    def action_run_audit(self):
        """Scans all active BOMs and generates audit exception records."""
        # Clear previous audit results for this company
        self.search([('company_id', '=', self.env.company.id)]).unlink()

        boms = self.env['mrp.bom'].search([('active', '=', True), ('company_id', 'in', (False, self.env.company.id))])
        records_to_create = []

        for bom in boms:
            # 1. Check if BOM has no components
            if not bom.bom_line_ids:
                records_to_create.append({
                    'name': _('BOM "%s" has no component lines defined.') % bom.display_name,
                    'severity': 'critical',
                    'bom_id': bom.id,
                    'exception_type': 'empty_bom',
                    'suggested_action': _('Add components to the BOM or archive it.'),
                    'company_id': self.env.company.id,
                })

            # 2. Check components with zero standard_price
            for line in bom.bom_line_ids:
                comp = line.product_id
                price = comp.with_company(self.env.company).standard_price
                if price <= 0:
                    records_to_create.append({
                        'name': _('Component "%(comp)s" in BOM "%(bom)s" has zero standard cost.') % {
                            'comp': comp.display_name,
                            'bom': bom.display_name,
                        },
                        'severity': 'critical',
                        'bom_id': bom.id,
                        'product_id': comp.id,
                        'exception_type': 'zero_material_cost',
                        'suggested_action': _('Update the component standard price or import supplier price.'),
                        'company_id': self.env.company.id,
                    })

            # 3. Check operations with zero work center costs_hour
            for op in bom.operation_ids:
                wc = op.workcenter_id
                if (wc.costs_hour or 0.0) <= 0:
                    records_to_create.append({
                        'name': _('Work Center "%(wc)s" for Operation "%(op)s" in BOM "%(bom)s" has zero hourly rate.') % {
                            'wc': wc.name,
                            'op': op.name,
                            'bom': bom.display_name,
                        },
                        'severity': 'warning',
                        'bom_id': bom.id,
                        'workcenter_id': wc.id,
                        'exception_type': 'zero_workcenter_rate',
                        'suggested_action': _('Set Cost per hour on the Work Center card.'),
                        'company_id': self.env.company.id,
                    })

            # 4. Check byproduct cost share sum
            if bom.byproduct_ids:
                total_share = sum(bom.byproduct_ids.mapped('cost_share'))
                if total_share > 100.0 or any(s < 0 for s in bom.byproduct_ids.mapped('cost_share')):
                    records_to_create.append({
                        'name': _('By-product cost shares in BOM "%s" total %.2f%% (must be between 0 and 100%%).') % (
                            bom.display_name, total_share
                        ),
                        'severity': 'critical',
                        'bom_id': bom.id,
                        'exception_type': 'invalid_cost_share',
                        'suggested_action': _('Adjust by-product cost_share percentages so total does not exceed 100%.'),
                        'company_id': self.env.company.id,
                    })

        if records_to_create:
            self.create(records_to_create)

        return {
            'type': 'ir.actions.act_window',
            'name': _('BOM Cost Exceptions Audit'),
            'res_model': 'mrp.cost.bom.exception',
            'view_mode': 'list,form',
            'target': 'current',
        }


class MrpCostConsumptionVariance(models.Model):
    _name = 'mrp.cost.consumption.variance'
    _description = 'Material Consumption Variance (Standard vs Actual)'
    _auto = False
    _order = 'variance_value desc'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', readonly=True)
    product_id = fields.Many2one('product.product', string='Finished Product', readonly=True)
    component_id = fields.Many2one('product.product', string='Raw Material / Component', readonly=True)
    planned_qty = fields.Float(string='Planned Qty', readonly=True)
    consumed_qty = fields.Float(string='Actual Consumed Qty', readonly=True)
    variance_qty = fields.Float(string='Variance Qty', readonly=True)
    variance_pct = fields.Float(string='Variance %', readonly=True)
    unit_cost = fields.Float(string='Standard Cost', readonly=True)
    variance_value = fields.Float(string='Variance Value', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date_done = fields.Datetime(string='Date', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    sm.id AS id,
                    mp.id AS production_id,
                    mp.product_id AS product_id,
                    sm.product_id AS component_id,
                    COALESCE(sm.product_uom_qty, 0.0) AS planned_qty,
                    COALESCE(sm.quantity, 0.0) AS consumed_qty,
                    (COALESCE(sm.quantity, 0.0) - COALESCE(sm.product_uom_qty, 0.0)) AS variance_qty,
                    CASE
                        WHEN COALESCE(sm.product_uom_qty, 0.0) > 0 THEN
                            ((COALESCE(sm.quantity, 0.0) - COALESCE(sm.product_uom_qty, 0.0)) / sm.product_uom_qty) * 100.0
                        ELSE 0.0
                    END AS variance_pct,
                    COALESCE((pp.standard_price->>mp.company_id::text)::numeric, (pp.standard_price->>'1')::numeric, sm.price_unit, 0.0) AS unit_cost,
                    (COALESCE(sm.quantity, 0.0) - COALESCE(sm.product_uom_qty, 0.0)) * COALESCE((pp.standard_price->>mp.company_id::text)::numeric, (pp.standard_price->>'1')::numeric, sm.price_unit, 0.0) AS variance_value,
                    mp.company_id AS company_id,
                    sm.date AS date_done
                FROM stock_move sm
                JOIN mrp_production mp ON sm.raw_material_production_id = mp.id
                JOIN product_product pp ON sm.product_id = pp.id
                WHERE sm.state = 'done'
            )
        """)


class MrpCostWipSnapshot(models.Model):
    _name = 'mrp.cost.wip.snapshot'
    _description = 'Work-in-Progress (WIP) Valuation Snapshot'
    _auto = False
    _order = 'net_wip_value desc'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', readonly=True)
    product_id = fields.Many2one('product.product', string='Finished Product', readonly=True)
    product_qty = fields.Float(string='Order Qty', readonly=True)
    qty_produced = fields.Float(string='Produced Qty', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date_start = fields.Datetime(string='Start Date', readonly=True)
    issued_material_cost = fields.Float(string='Raw Material Issued Cost', readonly=True)
    received_finished_cost = fields.Float(string='Finished Goods Received Cost', readonly=True)
    net_wip_value = fields.Float(string='Net WIP Value', readonly=True)
    state = fields.Selection([
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close')
    ], string='State', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH issued_materials AS (
                    SELECT
                        sm.raw_material_production_id AS production_id,
                        SUM(
                            COALESCE(
                                NULLIF(ABS(svl.value), 0),
                                sm.quantity * COALESCE(
                                    (pp.standard_price->>mp.company_id::text)::numeric,
                                    (pp.standard_price->>'1')::numeric,
                                    sm.price_unit,
                                    0.0
                                )
                            )
                        ) AS issued_cost
                    FROM stock_move sm
                    JOIN mrp_production mp ON sm.raw_material_production_id = mp.id
                    JOIN product_product pp ON sm.product_id = pp.id
                    LEFT JOIN stock_valuation_layer svl ON svl.stock_move_id = sm.id
                    WHERE sm.raw_material_production_id IS NOT NULL AND sm.state = 'done'
                    GROUP BY sm.raw_material_production_id
                ),
                received_finished AS (
                    SELECT
                        sm.production_id AS production_id,
                        SUM(
                            COALESCE(
                                NULLIF(ABS(svl.value), 0),
                                sm.quantity * COALESCE(
                                    (pp.standard_price->>mp.company_id::text)::numeric,
                                    (pp.standard_price->>'1')::numeric,
                                    sm.price_unit,
                                    0.0
                                )
                            )
                        ) AS finished_cost
                    FROM stock_move sm
                    JOIN mrp_production mp ON sm.production_id = mp.id
                    JOIN product_product pp ON sm.product_id = pp.id
                    LEFT JOIN stock_valuation_layer svl ON svl.stock_move_id = sm.id
                    WHERE sm.production_id IS NOT NULL AND sm.state = 'done'
                    GROUP BY sm.production_id
                )
                SELECT
                    mp.id AS id,
                    mp.id AS production_id,
                    mp.product_id AS product_id,
                    mp.product_qty AS product_qty,
                    COALESCE(mp.qty_producing, 0.0) AS qty_produced,
                    mp.company_id AS company_id,
                    mp.date_start AS date_start,
                    COALESCE(im.issued_cost, 0.0) AS issued_material_cost,
                    COALESCE(rf.finished_cost, 0.0) AS received_finished_cost,
                    (COALESCE(im.issued_cost, 0.0) - COALESCE(rf.finished_cost, 0.0)) AS net_wip_value,
                    mp.state AS state
                FROM mrp_production mp
                LEFT JOIN issued_materials im ON im.production_id = mp.id
                LEFT JOIN received_finished rf ON rf.production_id = mp.id
                WHERE mp.state IN ('confirmed', 'progress', 'to_close')
            )
        """)


class MrpCostWorkcenterAudit(models.Model):
    _name = 'mrp.cost.workcenter.audit'
    _description = 'Work Order Productivity & Timesheet Audit'
    _auto = False
    _order = 'production_id desc, id desc'

    workorder_id = fields.Many2one('mrp.workorder', string='Work Order', readonly=True)
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', readonly=True)
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center', readonly=True)
    name = fields.Char(string='Operation Name', readonly=True)
    duration_expected = fields.Float(string='Expected Duration (Min)', readonly=True)
    duration = fields.Float(string='Actual Duration (Min)', readonly=True)
    costs_hour = fields.Float(string='Hourly Rate', readonly=True)
    actual_labor_cost = fields.Float(string='Calculated Labor Cost', readonly=True)
    issue_flag = fields.Selection([
        ('zero_duration', 'Zero Actual Duration Recorded'),
        ('zero_cost_hour', 'Zero Workcenter Cost Rate'),
        ('both', 'Both Duration & Cost Rate Zero')
    ], string='Audit Flag', readonly=True)
    state = fields.Selection([
        ('pending', 'Waiting for another WO'),
        ('waiting', 'Waiting for components'),
        ('ready', 'Ready'),
        ('progress', 'In Progress'),
        ('done', 'Finished'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    wo.id AS id,
                    wo.id AS workorder_id,
                    wo.production_id AS production_id,
                    wo.workcenter_id AS workcenter_id,
                    wo.name AS name,
                    COALESCE(wo.duration_expected, 0.0) AS duration_expected,
                    COALESCE(wo.duration, 0.0) AS duration,
                    COALESCE(wc.costs_hour, 0.0) AS costs_hour,
                    (COALESCE(wo.duration, 0.0) / 60.0) * COALESCE(wc.costs_hour, 0.0) AS actual_labor_cost,
                    CASE
                        WHEN COALESCE(wo.duration, 0.0) = 0 AND COALESCE(wc.costs_hour, 0.0) = 0 THEN 'both'
                        WHEN COALESCE(wo.duration, 0.0) = 0 THEN 'zero_duration'
                        ELSE 'zero_cost_hour'
                    END AS issue_flag,
                    wo.state AS state,
                    wc.company_id AS company_id
                FROM mrp_workorder wo
                JOIN mrp_workcenter wc ON wo.workcenter_id = wc.id
                WHERE (COALESCE(wo.duration, 0.0) = 0 OR COALESCE(wc.costs_hour, 0.0) = 0)
                  AND wo.state IN ('progress', 'done')
            )
        """)
