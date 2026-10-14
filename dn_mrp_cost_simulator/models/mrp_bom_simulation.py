from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MrpBomSimulation(models.Model):
    _name = 'mrp.bom.simulation'
    _description = 'Manufacturing Cost Simulation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Simulation Ref',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    version = fields.Integer(string='Version', default=1, required=True, tracking=True)
    description = fields.Char(
        string='Scenario Description',
        required=True,
        tracking=True,
        help='e.g., Q4 Raw Material Hike (+10%), Labor Rate Adjustment, Energy Surcharge'
    )
    parent_simulation_id = fields.Many2one(
        'mrp.bom.simulation',
        string='Parent Simulation',
        ondelete='set null',
        copy=False,
        help='Preceding version or base snapshot'
    )
    revision_ids = fields.One2many(
        'mrp.bom.simulation',
        'parent_simulation_id',
        string='Derived Revisions'
    )
    bom_id = fields.Many2one(
        'mrp.bom',
        string='Bill of Materials',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        related='bom_id.product_tmpl_id',
        store=True,
        readonly=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product Variant',
        compute='_compute_product_id',
        store=True,
        readonly=False
    )
    product_qty = fields.Float(
        string='Simulated Output Qty',
        default=1.0,
        digits='Product Unit of Measure',
        required=True,
        tracking=True
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        compute='_compute_product_uom',
        store=True,
        readonly=False
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Company Currency',
        related='company_id.currency_id',
        readonly=True
    )
    target_currency_id = fields.Many2one(
        'res.currency',
        string='Simulation Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
        help='Target currency for simulation analysis'
    )
    exchange_rate = fields.Float(
        string='Exchange Rate',
        default=1.0,
        digits=(12, 6),
        help='Multiplication factor from Company Currency to Target Currency'
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Plant / Warehouse Context',
        help='Warehouse or facility context for location-aware costing simulation'
    )
    date_simulation = fields.Date(
        string='Simulation Date',
        default=fields.Date.context_today,
        required=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('applied', 'Applied to Production'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)

    costing_basis = fields.Selection([
        ('standard', 'Standard Cost (Product Form)'),
        ('svl_latest', 'Latest Inventory Valuation Layer (SVL)'),
        ('custom', 'Current Cost + Manual Hypothetical Overrides')
    ], string='Baseline Cost Source', default='standard', required=True)
    explode_subassemblies = fields.Boolean(
        string='Explode Multi-level BOMs',
        default=True,
        help='Recursively deconstructs sub-assemblies down to raw materials and collects all operations across all levels.'
    )

    # Cost breakdown summary
    total_material_cost = fields.Monetary(
        string='Total Direct Materials',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )
    total_labor_cost = fields.Monetary(
        string='Total Direct Labor & Routing',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )
    total_overhead_cost = fields.Monetary(
        string='Overhead Cost',
        currency_field='currency_id',
        default=0.0
    )
    total_byproduct_deduction = fields.Monetary(
        string='By-product Deductions',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )
    total_cost = fields.Monetary(
        string='Net Total Manufacturing Cost',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )
    unit_cost_simulated = fields.Monetary(
        string='Simulated Unit Cost',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )
    unit_cost_target_currency = fields.Monetary(
        string='Unit Cost (Sim. Currency)',
        currency_field='target_currency_id',
        compute='_compute_totals',
        store=True
    )
    unit_cost_current = fields.Monetary(
        string='Current Product Standard Cost',
        currency_field='currency_id',
        compute='_compute_current_cost',
        store=True
    )
    cost_variance = fields.Monetary(
        string='Cost Variance (Abs)',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )
    cost_variance_pct = fields.Float(
        string='Cost Variance (%)',
        compute='_compute_totals',
        store=True
    )

    line_ids = fields.One2many(
        'mrp.bom.simulation.line',
        'simulation_id',
        string='Component Breakdown',
        copy=True
    )
    operation_ids = fields.One2many(
        'mrp.bom.simulation.operation',
        'simulation_id',
        string='Routing & Labor Breakdown',
        copy=True
    )
    byproduct_ids = fields.One2many(
        'mrp.bom.simulation.byproduct',
        'simulation_id',
        string='By-products & Yield Allocations',
        copy=True
    )
    notes = fields.Html(string='Simulation Notes & Analysis')

    _check_version_positive = models.Constraint(
        'CHECK(version > 0)',
        'Simulation version must be strictly positive!'
    )
    _check_qty_positive = models.Constraint(
        'CHECK(product_qty > 0)',
        'Simulation quantity must be greater than zero!'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('mrp.bom.simulation') or _('SIM/%s') % fields.Date.today().year
        return super().create(vals_list)

    @api.depends('bom_id')
    def _compute_product_id(self):
        for sim in self:
            if sim.bom_id:
                sim.product_id = sim.bom_id.product_id or sim.bom_id.product_tmpl_id.product_variant_id
            else:
                sim.product_id = False

    @api.depends('bom_id')
    def _compute_product_uom(self):
        for sim in self:
            if sim.bom_id:
                sim.product_uom_id = sim.bom_id.product_uom_id
            elif sim.product_id:
                sim.product_uom_id = sim.product_id.uom_id
            else:
                sim.product_uom_id = False

    @api.depends('product_id', 'product_tmpl_id', 'company_id')
    def _compute_current_cost(self):
        for sim in self:
            prod = sim.product_id or (sim.product_tmpl_id and sim.product_tmpl_id.product_variant_id)
            if prod:
                sim.unit_cost_current = prod.with_company(sim.company_id).standard_price
            else:
                sim.unit_cost_current = 0.0

    @api.depends(
        'line_ids.subtotal_cost',
        'operation_ids.subtotal_cost',
        'total_overhead_cost',
        'byproduct_ids.cost_share',
        'product_qty',
        'unit_cost_current',
        'exchange_rate'
    )
    def _compute_totals(self):
        for sim in self:
            mat_cost = sum(sim.line_ids.mapped('subtotal_cost'))
            labor_cost = sum(sim.operation_ids.mapped('subtotal_cost'))
            gross_cost = mat_cost + labor_cost + sim.total_overhead_cost

            # By-product cost share deduction
            total_byproduct_pct = sum(sim.byproduct_ids.mapped('cost_share'))
            # Calculate allocated cost to each byproduct
            byproduct_deduction = 0.0
            for bp in sim.byproduct_ids:
                bp_cost = gross_cost * (bp.cost_share / 100.0) if bp.cost_share else 0.0
                bp.allocated_cost = bp_cost
                byproduct_deduction += bp_cost

            net_total = max(0.0, gross_cost - byproduct_deduction)
            qty = sim.product_qty or 1.0
            unit_sim = net_total / qty

            sim.total_material_cost = mat_cost
            sim.total_labor_cost = labor_cost
            sim.total_byproduct_deduction = byproduct_deduction
            sim.total_cost = net_total
            sim.unit_cost_simulated = unit_sim
            sim.unit_cost_target_currency = unit_sim * (sim.exchange_rate or 1.0)

            sim.cost_variance = unit_sim - sim.unit_cost_current
            if sim.unit_cost_current > 0:
                sim.cost_variance_pct = (sim.cost_variance / sim.unit_cost_current) * 100.0
            else:
                sim.cost_variance_pct = 100.0 if unit_sim > 0 else 0.0

    # -------------------------------------------------------------------------
    # High-Speed Recursive BOM Traversal (In-Memory Dictionary Engine)
    # -------------------------------------------------------------------------
    def _fetch_product_baseline_cost(self, product, basis, company):
        """Fetch baseline unit cost for a raw material or sub-assembly."""
        if basis == 'svl_latest':
            # Check latest SVL unit cost
            svl = self.env['stock.valuation.layer'].search([
                ('product_id', '=', product.id),
                ('company_id', '=', company.id),
                ('remaining_qty', '>', 0)
            ], order='id desc', limit=1)
            if svl and svl.unit_cost > 0:
                return svl.unit_cost
            # Fallback to standard price
            return product.with_company(company).standard_price
        return product.with_company(company).standard_price

    def _build_bom_tree(self, bom, factor, level=0, visited_boms=None):
        """
        Recursively extract BOM lines and operations into Python dictionaries.
        Guards against recursive circular BOM definitions and avoids N+1 queries.
        """
        if visited_boms is None:
            visited_boms = set()

        if bom.id in visited_boms:
            raise ValidationError(_('Circular BOM loop detected for BOM: %s!') % bom.display_name)
        visited_boms.add(bom.id)

        line_results = []
        op_results = []
        byproduct_results = []

        company = self.company_id or self.env.company
        basis = self.costing_basis

        # 1. Process Operations for this BOM level
        for op in bom.operation_ids:
            duration = (op.time_cycle_manual or 0.0) * factor
            rate = op.workcenter_id.costs_hour or 0.0
            op_results.append({
                'operation_id': op.id,
                'name': op.name,
                'sequence': op.sequence,
                'workcenter_id': op.workcenter_id.id,
                'time_cycle_manual': op.time_cycle_manual,
                'simulated_duration': duration,
                'original_costs_hour': rate,
                'simulated_costs_hour': rate,
                'subtotal_cost': (duration / 60.0) * rate,
            })

        # 2. Process By-products
        if level == 0 and bom.byproduct_ids:
            for bp in bom.byproduct_ids:
                byproduct_results.append({
                    'byproduct_id': bp.id,
                    'product_id': bp.product_id.id,
                    'product_qty': bp.product_qty * factor,
                    'product_uom_id': bp.product_uom_id.id,
                    'cost_share': bp.cost_share or 0.0,
                    'allocated_cost': 0.0,
                })

        # 3. Process Components
        for line in bom.bom_line_ids:
            product = line.product_id
            line_qty = line.product_qty * factor

            # Look for sub-BOM
            sub_bom = self.env['mrp.bom']._bom_find(
                product,
                company_id=company.id,
                bom_type=False
            )[product]

            is_phantom = sub_bom and sub_bom.type == 'phantom'

            if sub_bom and (is_phantom or self.explode_subassemblies):
                # Deconstruct sub-assembly recursively down to raw materials and operations
                sub_factor = line_qty / (sub_bom.product_qty or 1.0)
                sub_lines, sub_ops, sub_byproducts = self._build_bom_tree(
                    sub_bom, sub_factor, level=level + 1, visited_boms=set(visited_boms)
                )
                line_results.extend(sub_lines)
                op_results.extend(sub_ops)
            else:
                base_cost = self._fetch_product_baseline_cost(product, basis, company)
                line_data = {
                    'bom_line_id': line.id,
                    'level': level + 1,
                    'product_id': product.id,
                    'product_qty': line_qty,
                    'product_uom_id': line.product_uom_id.id,
                    'scrap_rate': 0.0,
                    'qty_with_scrap': line_qty,
                    'original_cost': base_cost,
                    'simulated_cost': base_cost,
                    'subtotal_cost': line_qty * base_cost,
                    'is_subassembly': bool(sub_bom),
                    'sub_bom_id': sub_bom.id if sub_bom else False,
                    'is_phantom': bool(is_phantom),
                    'notes': _('Sub-assembly: %s') % sub_bom.display_name if sub_bom else ''
                }
                line_results.append(line_data)

        return line_results, op_results, byproduct_results

    def action_load_from_bom(self):
        """Deconstructs the target BOM and populates the simulation lines."""
        self.ensure_one()
        if not self.bom_id:
            raise UserError(_('Please select a Bill of Materials first.'))

        # Clear existing lines
        self.line_ids.unlink()
        self.operation_ids.unlink()
        self.byproduct_ids.unlink()

        factor = self.product_qty / (self.bom_id.product_qty or 1.0)
        lines, ops, byproducts = self._build_bom_tree(self.bom_id, factor, level=0)

        # Batch create lines
        line_vals = [dict(l, simulation_id=self.id) for l in lines]
        op_vals = [dict(o, simulation_id=self.id) for o in ops]
        bp_vals = [dict(b, simulation_id=self.id) for b in byproducts]

        if line_vals:
            self.env['mrp.bom.simulation.line'].create(line_vals)
        if op_vals:
            self.env['mrp.bom.simulation.operation'].create(op_vals)
        if bp_vals:
            self.env['mrp.bom.simulation.byproduct'].create(bp_vals)

        self._compute_totals()
        self.state = 'calculated'
        self.message_post(body=_('BOM structure loaded with %d components and %d operations.') % (
            len(line_vals), len(op_vals)
        ))
        return True

    def action_recalculate(self):
        """Recalculates all subtotal costs based on injected prices."""
        self.ensure_one()
        for line in self.line_ids:
            line._compute_subtotal()
        for op in self.operation_ids:
            op._compute_subtotal()
        self._compute_totals()
        self.state = 'calculated'
        return True

    def action_approve(self):
        """Mark simulation scenario approved by management."""
        self.ensure_one()
        if self.state not in ('calculated', 'draft'):
            raise UserError(_('Only calculated simulations can be approved.'))
        self.state = 'approved'
        self.message_post(body=_('Simulation approved with simulated unit cost: %s %s.') % (
            self.unit_cost_simulated, self.currency_id.symbol
        ))
        return True

    def action_create_version(self):
        """Creates a new version snapshot (V+1) branching from this simulation."""
        self.ensure_one()
        new_version = self.version + 1
        new_sim = self.copy({
            'name': _('New'),
            'version': new_version,
            'parent_simulation_id': self.id,
            'description': _('%s (Rev %d)') % (self.description, new_version),
            'state': 'draft',
            'date_simulation': fields.Date.context_today(self),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Simulation Revision'),
            'res_model': 'mrp.bom.simulation',
            'res_id': new_sim.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_apply_simulation(self):
        """
        Applies simulated costs to production:
        - Updates the product standard_price
        - Logs the adjustment tracking in chatter
        """
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved simulations can be applied to real production.'))

        product = self.product_id or (self.product_tmpl_id and self.product_tmpl_id.product_variant_id)
        if not product:
            raise UserError(_('No valid product found to update standard cost.'))

        old_cost = product.with_company(self.company_id).standard_price
        new_cost = self.unit_cost_simulated

        # Update product cost in company
        product.with_company(self.company_id).standard_price = new_cost

        self.state = 'applied'
        msg = _(
            'Applied Simulation %(name)s (V%(ver)s): '
            'Product "%(prod)s" standard cost updated from %(old).4f %(cur)s to %(new).4f %(cur)s.'
        ) % {
            'name': self.name,
            'ver': self.version,
            'prod': product.display_name,
            'old': old_cost,
            'new': new_cost,
            'cur': self.currency_id.symbol
        }
        self.message_post(body=msg)
        product.message_post(body=msg)
        return True

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancelled'
        return True

    def action_set_draft(self):
        self.ensure_one()
        self.state = 'draft'
        return True


class MrpBomSimulationLine(models.Model):
    _name = 'mrp.bom.simulation.line'
    _description = 'BOM Simulation Component Line'
    _order = 'level asc, id asc'

    simulation_id = fields.Many2one(
        'mrp.bom.simulation',
        string='Simulation',
        required=True,
        ondelete='cascade'
    )
    bom_line_id = fields.Many2one('mrp.bom.line', string='Original BOM Line')
    level = fields.Integer(string='BOM Level', default=1)
    product_id = fields.Many2one(
        'product.product',
        string='Component',
        required=True
    )
    product_qty = fields.Float(
        string='Base Quantity',
        required=True,
        digits='Product Unit of Measure'
    )
    product_uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    scrap_rate = fields.Float(
        string='Scrap Rate (%)',
        default=0.0,
        help='Anticipated scrap/waste percentage'
    )
    qty_with_scrap = fields.Float(
        string='Qty (Incl. Scrap)',
        compute='_compute_qty_with_scrap',
        store=True,
        digits='Product Unit of Measure'
    )
    original_cost = fields.Float(
        string='Baseline Cost',
        digits='Product Price',
        help='Original baseline unit cost from inventory valuation'
    )
    simulated_cost = fields.Float(
        string='Simulated Unit Cost',
        digits='Product Price',
        required=True,
        help='Hypothetical or injected unit cost'
    )
    price_variance_pct = fields.Float(
        string='Cost Delta %',
        compute='_compute_subtotal',
        store=True
    )
    subtotal_cost = fields.Float(
        string='Subtotal Cost',
        compute='_compute_subtotal',
        store=True,
        digits='Product Price'
    )
    is_subassembly = fields.Boolean(string='Is Sub-Assembly')
    sub_bom_id = fields.Many2one('mrp.bom', string='Sub BOM')
    is_phantom = fields.Boolean(string='Kit / Phantom')
    notes = fields.Char(string='Notes')

    @api.depends('product_qty', 'scrap_rate')
    def _compute_qty_with_scrap(self):
        for line in self:
            factor = 1.0 + (line.scrap_rate / 100.0) if line.scrap_rate else 1.0
            line.qty_with_scrap = line.product_qty * factor

    @api.depends('qty_with_scrap', 'simulated_cost', 'original_cost')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal_cost = (line.qty_with_scrap or 0.0) * (line.simulated_cost or 0.0)
            if line.original_cost > 0:
                line.price_variance_pct = ((line.simulated_cost - line.original_cost) / line.original_cost) * 100.0
            else:
                line.price_variance_pct = 100.0 if line.simulated_cost > 0 else 0.0


class MrpBomSimulationOperation(models.Model):
    _name = 'mrp.bom.simulation.operation'
    _description = 'BOM Simulation Routing Operation'
    _order = 'sequence asc, id asc'

    simulation_id = fields.Many2one(
        'mrp.bom.simulation',
        string='Simulation',
        required=True,
        ondelete='cascade'
    )
    operation_id = fields.Many2one('mrp.routing.workcenter', string='Routing Operation')
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Operation Name', required=True)
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Work Center',
        required=True
    )
    time_cycle_manual = fields.Float(
        string='Standard Duration (Min)',
        help='Standard cycle duration per unit'
    )
    simulated_duration = fields.Float(
        string='Simulated Duration (Min)',
        required=True,
        help='Simulated operational duration in minutes'
    )
    original_costs_hour = fields.Float(
        string='Original Hourly Rate',
        digits='Product Price'
    )
    simulated_costs_hour = fields.Float(
        string='Simulated Hourly Rate',
        required=True,
        digits='Product Price',
        help='Allows hypothetical workcenter wage/energy rate injection'
    )
    subtotal_cost = fields.Float(
        string='Labor / Machine Cost',
        compute='_compute_subtotal',
        store=True,
        digits='Product Price'
    )

    @api.depends('simulated_duration', 'simulated_costs_hour')
    def _compute_subtotal(self):
        for op in self:
            duration_hours = (op.simulated_duration or 0.0) / 60.0
            op.subtotal_cost = duration_hours * (op.simulated_costs_hour or 0.0)


class MrpBomSimulationByproduct(models.Model):
    _name = 'mrp.bom.simulation.byproduct'
    _description = 'BOM Simulation Byproduct Allocation'

    simulation_id = fields.Many2one(
        'mrp.bom.simulation',
        string='Simulation',
        required=True,
        ondelete='cascade'
    )
    byproduct_id = fields.Many2one('mrp.bom.byproduct', string='BOM Byproduct')
    product_id = fields.Many2one(
        'product.product',
        string='By-product',
        required=True
    )
    product_qty = fields.Float(
        string='Estimated Qty',
        required=True,
        digits='Product Unit of Measure'
    )
    product_uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    cost_share = fields.Float(
        string='Cost Share (%)',
        required=True,
        help='Percentage of total manufacturing cost allocated to this by-product'
    )
    allocated_cost = fields.Float(
        string='Allocated Cost Deduction',
        digits='Product Price',
        help='Amount subtracted from main product cost'
    )
