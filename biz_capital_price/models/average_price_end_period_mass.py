# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import threading
import json
import traceback  # thêm ở đầu file

from datetime import timedelta, datetime, time
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)

class AveragePriceEndPeriodMass(models.Model):
    _name = "average.price.end.period.mass"
    _description = "Average Price End Period Mass"
    _order = 'from_date desc'

    def _product_ids_domain(self):
        return [("categ_id", "!=", False), ("categ_id.property_cost_method", "in", ["fifo", "average"])]

    name = fields.Char(string="Char", compute="_compute_name", store=True)
    from_date = fields.Date(string="From Date", copy=False)
    to_date = fields.Date(string="To Date", copy=False)
    product_ids = fields.Many2many(comodel_name="product.product",
                                   relation="average_price_end_period_mass_product_rel", column1="period_id",
                                   column2="product_id", domain=_product_ids_domain, string="Product", copy=True)

    warehouse_ids = fields.Many2many("stock.warehouse", string='Warehouse')
    is_finished_products = fields.Boolean(string="+ Finished products have been manufactured", copy=False, default=False)
    allocation_rate = fields.Float("Allocation Rate")
    end_cost_allocation_ids = fields.One2many("end.period.cost.allocation",'mass_period_id', 'Cost')
    total_allocation_value = fields.Float(string="Total value allocation cost", compute='compute_value')

    period_ids = fields.One2many("average.capital.price.end.period" ,'mass_period_id', 'Period')
    period_count = fields.Integer(compute='compute_period_count')
    state = fields.Selection([
        ('new', 'Mới'),
        ('loading', 'Đang tải'),
        ('done', 'Hoàn thành'),
        ('error', 'Lỗi')
    ], default='new', string='Trạng thái', copy=False)
    
    error = fields.Char("Lỗi")
    sum_quantity_import = fields.Float("Quantity Import", compute=False)
    data_quantity_import = fields.Json('Data Quantity Import',compute=False)
    carryover_move_id = fields.Many2one('account.move', string='Carryover Move', copy=False)
    carryover_journal_id = fields.Many2one('account.journal', string='Journal', required=False)
    carryover_debit_account_id = fields.Many2one('account.account', string='Debit Account', required=False)
    default_carryover_account_ids = fields.Many2many('account.account', string='Default carryover account',
        compute='_compute_default_carryover_account_id', store=True, readonly=False)
    
    apply_inventory = fields.Boolean(string="Áp dụng kiểm kê đầu kỳ")
    exclude_begin_period = fields.Boolean(string="Không tính đầu kỳ")

    def _get_layer_date_range(self):
        self.ensure_one()
        datetime_from_date = datetime.combine(self.from_date, time.min) - timedelta(hours=7)
        datetime_to_date = datetime.combine(self.to_date, time.max) - timedelta(hours=7)
        datefrom = datetime_from_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        dateto = datetime_to_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return datefrom, dateto

    def _get_distinct_layer_product_ids(self, location_field, location_usage):
        self.ensure_one()
        datefrom, dateto = self._get_layer_date_range()
        query = """
            SELECT DISTINCT svl.product_id
            FROM stock_valuation_layer svl
            JOIN stock_move sm ON sm.id = svl.stock_move_id
            JOIN stock_location sl ON sl.id = sm.{location_field}
            WHERE svl.create_date >= %s
              AND svl.create_date <= %s
              AND sl.usage = %s
              AND svl.product_id IS NOT NULL
        """.format(location_field=location_field)
        self.env.cr.execute(query, (datefrom, dateto, location_usage))
        return [row[0] for row in self.env.cr.fetchall()]

    def action_get_product_nvl(self):
        self.ensure_one()
        product_ids = self._get_distinct_layer_product_ids('location_dest_id', 'production')
        self.product_ids = [(6, 0, product_ids)]

    def action_get_product_tp(self):
        self.ensure_one()
        product_ids = self._get_distinct_layer_product_ids('location_id', 'production')
        self.product_ids = [(6, 0, product_ids)]

    def action_get_product_storable(self):
        self.ensure_one()
        product_ids = self._get_distinct_layer_product_ids('location_id', 'inventory')
        self.write({
            'product_ids': [(6, 0, product_ids)],
            'apply_inventory': True,
        })


    @api.depends('create_date')
    def _compute_default_carryover_account_id(self):
        for res in self:
            if not res.default_carryover_account_ids:
                account_ids = self.env['account.account'].search([
                    ('code', '=', '6211'),
                ])
                res.default_carryover_account_ids = [(6,0, account_ids.ids)]

    def update_quantity_import(self):
        data = {}
        for line in self.period_ids.mapped('period_line_ids'):
            pid = str(line.product_id.id)
            data[pid] = data.get(pid, 0) + (line.quantity_in_period or 0)
        self.write({
            'sum_quantity_import': sum(data.values()),
            'data_quantity_import': json.dumps(data),
        })
        
    @api.depends("period_ids")
    def compute_period_count(self):
        for res in self:
            res.period_count = len(res.period_ids)

    def action_open_period(self):
        self = self.sudo()
        action = self.env.ref("biz_capital_price.action_average_capital_price_end_period").read()[0]
        action['domain'] = [('mass_period_id','=', self.id)]
        action['context'] = {'default_mass_period_id': self.id}
        return action

    @api.depends('end_cost_allocation_ids')
    def compute_value(self): 
        for res in self:
            res.total_allocation_value = sum(res.end_cost_allocation_ids.mapped("value"))

    @api.depends("from_date", "to_date")
    def _compute_name(self):
        for record in self:
            if record.from_date and record.to_date:
                record.name = "%s-%s" % (
                    record.from_date.strftime("%d/%m/%Y") or '', record.to_date.strftime("%d/%m/%Y") or '')
            else:
                record.name = False

    def action_confirm(self):
        self.ensure_one()
        with self.pool.cursor() as cr:
            cr.execute(
                "SELECT state FROM average_price_end_period_mass WHERE id = %s FOR UPDATE",
                (self.id,)
            )
            row = cr.fetchone()
            if row and row[0] == 'loading':
                raise ValidationError(_("Đang xử lý, vui lòng chờ..."))
            cr.execute(
                "UPDATE average_price_end_period_mass SET state = 'loading' WHERE id = %s",
                (self.id,)
            )
            cr.commit()

        self._start_confirm_mass()

    def _start_confirm_mass(self):
        t = threading.Thread(target=self._thread_function_confirm_mass, daemon=True)
        t.start()

    def _thread_function_confirm_mass(self):
        uid = self.env.uid
        context = self.env.context
        record_id = self.id
        with self.pool.cursor() as new_cr:
            new_env = api.Environment(new_cr, uid, context)
            self = new_env['average.price.end.period.mass'].browse(record_id)
            try:
                self.do_action_confirm()
                self.write({'state': 'done'})
                new_cr.commit()
            except Exception as e:
                tb = traceback.format_exc()
                _logger.error(f"########Error mass confirm {record_id}\n{tb}")
                try:
                    new_cr.rollback()
                except Exception:
                    pass
                with self.pool.cursor() as err_cr:
                    err_env = api.Environment(err_cr, uid, context)
                    err_env['average.price.end.period.mass'].browse(record_id).write({
                        'state': 'error',
                        'error': tb[:2048],
                    })
                    err_cr.commit()

    def do_action_confirm(self):
        self.ensure_one()
        _logger.info(f"########Start mass confirm {self.id}")
        ModelCapital = self.env['average.capital.price.end.period']
        self.period_ids.unlink()
        self.set_price_internal_layers_to_zero()
        
        previous_periods = False   
        last = ModelCapital.search([
            ("to_date", '<', self.from_date),
            ('is_finished_products', '=', self.is_finished_products),
            ('mass_period_id.state', '=', 'done')
        ], order='to_date desc', limit=1)

        if last:
            previous_periods = ModelCapital.search([
                ('from_date', '=', last.from_date),
                ('to_date', '=', last.to_date),
                ('is_finished_products', '=', self.is_finished_products),
                ('mass_period_id.state', '=', 'done')
            ])

        vals = {
            'mass_period_id': self.id,
            'from_date': self.from_date,
            'to_date': self.to_date,
            'product_ids': [(6, 0, self.product_ids.ids)],
            'is_finished_products': self.is_finished_products,
            'allocation_rate': self.allocation_rate,
            'previous_period_ids': [(6,0,previous_periods.ids)] if previous_periods else False,
            'end_cost_allocation_ids': [(0, 0, {
                "cost_id": line.cost_id.id,
                "date": line.date,
                "total_cost": line.total_cost,
                "value": line.value,
                "note": line.note,
            }) for line in self.end_cost_allocation_ids],
        }
        period = ModelCapital.create(vals)
        period.action_pricing()

        self.check_create_line_dup_remanufacturing_orders()

        _logger.info(f"########End step1 mass confirm {self.id}")
        self.update_quantity_import()

        _logger.info(f"########End step2 mass confirm {self.id}")
        self._process_internal_transfers()
        _logger.info(f"########End done mass confirm {self.id}")

    def set_price_internal_layers_to_zero(self):  
        if not self.product_ids:
            return
        datefrom, dateto = self._get_layer_date_range()
        self.env.cr.execute("""
            UPDATE stock_valuation_layer
            SET unit_cost = 0, value = 0
            WHERE product_id = ANY(%s)
            AND interval_stock_move_line_id IS NOT NULL
            AND create_date >= %s
            AND create_date <= %s
        """, (self.product_ids.ids, datefrom, dateto))

    def check_create_line_dup_remanufacturing_orders(self):
        origin_lines = self.period_ids.mapped('period_line_ids')
        if not origin_lines:
            return
        is_finished_products = self.is_finished_products or self.exclude_begin_period

        # Batch query thay vì N calls
        ModelLayer = self.env["stock.valuation.layer"]
        datetime_from_date = datetime.combine(self.from_date, time.min) - timedelta(hours=7)
        datetime_to_date = datetime.combine(self.to_date, time.max) - timedelta(hours=7)

        if self.apply_inventory:
            domain_loc = [("stock_move_id.location_id.usage", "in", ["production", "inventory"])]
        else:
            domain_loc = [("stock_move_id.location_id.usage", "in", ["production"])]

        domain2 = [
            ("quantity", '<', 0),
            ('stock_move_id.unbuild_id', '!=', False),
            ("stock_move_id.location_dest_id.usage", '=', 'production'),
        ]
        all_layers = ModelLayer.search(expression.AND([
            expression.OR([domain_loc, domain2]),
            [
                ("product_id", "in", origin_lines.mapped('product_id.id')),
                ("create_date", ">=", datetime_from_date),
                ("create_date", "<=", datetime_to_date),
                ('stock_move_id.production_id.is_remanufacturing_order', '=', True),
            ]
        ]))

        reman_prod = {}
        for layer in all_layers:
            reman_prod.setdefault(layer.product_id.id, []).append(layer.id)

        if not reman_prod:
            return

        # _logger.info(f"######## reman_prod {self.id} {reman_prod}")

        # Precompute previous period lines by product (tránh traversal lặp lại per line)
        all_prev_lines = self.period_ids.mapped('previous_period_ids').mapped('period_line_ids')
        prev_lines_by_prod = {}
        for pl in all_prev_lines:
            prev_lines_by_prod.setdefault(pl.product_id.id, []).append(pl)

        for prod, layers in reman_prod.items():
            reman_lines = origin_lines.filtered(lambda x, p=prod: x.product_id.id == p)
            initital_value = initital_quantity = 0
            previous_product = prev_lines_by_prod.get(prod, [])
            if previous_product:
                initital_quantity = sum(pl.total_quantity_import for pl in previous_product)
                if is_finished_products:
                    initital_quantity += sum(pl.initital_quantity for pl in previous_product)

                if initital_quantity:
                    initital_value = sum(pl.actual_value_import for pl in previous_product)
                    if is_finished_products:
                        initital_value += sum(pl.initital_value for pl in previous_product)

                initital_quantity -= abs(sum(pl.total_quantity_export for pl in previous_product))
                initital_value -= abs(sum(pl.total_value_export for pl in previous_product))

            vals = {
                'product_id': prod,
                'initital_quantity': abs(initital_quantity),
                'initital_value': abs(initital_value),
                'stock_valuation_layer_ids': [(6, 0, layers)],
                'is_priority_th2': True,
                'is_internal': False,
            }
            for lin in reman_lines:
                lin.copy(vals)

    def _process_internal_transfers(self):
        all_lines = self.period_ids.mapped('period_line_ids')
        all_lines.compute_actual_value()
        capital_price_priority = int(self.env['ir.config_parameter'].sudo().get_param('biz_capital_price.capital_price_priority', default=10))
        self.action_update_not_internal_line(all_lines, capital_price_priority)
        for period in self.period_ids:
            _logger.info(f"########Start update internal transfer price {self.id} period {period.id}")
            period.update_internal_transfer_price()

    def action_update_not_internal_line(self, lines, capital_price_priority=10):
        if not self.is_finished_products:
            self._update_layers(lines)
            return True

        origin_lines = lines
        lines = lines.filtered(lambda x: not x.is_priority_th2)

        # Build priority chains iteratively and cache results to avoid repeated calls
        priorities = []
        # Get priority chains up to 10 levels deep

        prev = self.product_ids.ids
        for _ in range(capital_price_priority):
            if not prev:
                priorities.append([])
                prev = []
                break
            p = self._get_priority_th1(prev)
            if not p:
                break
            priorities.append(p)
            prev = p

        # Process priorities from deepest to first (UT10 -> UT1)
        for idx, p in reversed(list(enumerate(priorities))):
            _logger.info(f"######## UT{idx + 1} {self.id} {p}")
            if not p:
                continue
            # select lines for this priority (single pass)
            line1 = lines.filtered(lambda x: x.product_id.id in set(p))
            if not line1:
                continue
            line1.compute_layers_all(True)
            line1.compute_total()
            line1.compute_actual_value()
            self._update_layers(line1, level=1)
            # remove processed lines from remaining set
            lines -= line1

        # Remaining lines
        if lines:
            lines.compute_layers_all()
            lines.compute_total()
            lines.compute_actual_value()
            self._update_layers(lines, level=1)

        # Process duplicated priority lines last
        lines_dup = origin_lines.filtered(lambda x: x.is_priority_th2)
        if lines_dup:
            lines_dup.compute_layers_all()
            lines_dup.compute_total()
            lines_dup.compute_actual_value()
            self._update_layers(lines_dup, level=3)

        return True

    def update_value_per_unit_th2(self, lines):
        ModelLayer = self.env["stock.valuation.layer"]
        all_product_ids = lines.mapped('product_id.id')
        datetime_from_date = datetime.combine(self.from_date, time.min) - timedelta(hours=7)
        datetime_to_date = datetime.combine(self.to_date, time.max) - timedelta(hours=7)
        domain = [
            ("product_id", "in", all_product_ids), 
            ("create_date", ">=", datetime_from_date),
            ("create_date", "<=", datetime_to_date), 
            ("stock_move_id", "!=", False),
            ("stock_move_id.production_id", "=", False), 
            '|',
            ("stock_move_id.location_dest_id.usage", "in", ["customer",'inventory']),
            ("stock_move_id.location_id.usage", "in", ["customer"]),
        ]
        all_layers = ModelLayer.search(domain)
        layers_by_product = {}
        for layer in all_layers:
            layers_by_product.setdefault(layer.product_id.id, ModelLayer)
            layers_by_product[layer.product_id.id] |= layer
        
        for line in lines:
            self.update_value_layers(layers_by_product.get(line.product_id.id, ModelLayer), line.ex_warehouse_price)
        
        self._update_move_credit_debit_batch(all_layers)
        lines.compute_total_export()

    def _update_layers(self, lines, level=0):
        if not self.is_finished_products:
            lines = lines.filtered(lambda x: x.value_per_unit != 0)
            self._update_warehouse_delivery(lines)
            self._update_warehouse_delivery_ex_warehouse(lines)
        else:
            self._update_layer_finished_th1(lines, level)
            lines.compute_ex_warehouse_price()
            self._update_layer_finished_th2(lines, level)
            if level == 3:
                self.update_value_per_unit_th2(lines)
            else:
                self._update_layer_finished_th3(lines, level)
            self._update_layer_finished_th4(lines, level)

    def _update_warehouse_delivery(self, lines):
        ModelLayer = self.env["stock.valuation.layer"]
        datetime_from_date = datetime.combine(self.from_date, time.min) - timedelta(hours=7)
        datetime_to_date = datetime.combine(self.to_date, time.max) - timedelta(hours=7)

        all_product_ids = lines.mapped('product_id.id')
        all_layers = self.env["stock.valuation.layer"].search([
            ("product_id", "in", all_product_ids),
            ("create_date", ">=", datetime_from_date),
            ("create_date", "<=", datetime_to_date),
            ("stock_move_id", "!=", False),
            ("stock_move_id.production_id", "=", False),
            '|',
            ("stock_move_id.location_dest_id.usage", "in", ['customer', 'production']),
            ("stock_move_id.location_id.usage", "in", ["production"]),
        ])
        layers_by_product = {}
        for layer in all_layers:
            layers_by_product.setdefault(layer.product_id.id, ModelLayer)
            layers_by_product[layer.product_id.id] |= layer

        for line in lines:
            self.update_value_layers(layers_by_product.get(line.product_id.id, ModelLayer), line.value_per_unit)

        self._update_move_credit_debit_batch(all_layers)

    def _update_warehouse_delivery_ex_warehouse(self, lines):
        ModelLayer = self.env["stock.valuation.layer"]
        datetime_from_date = datetime.combine(self.from_date, time.min) - timedelta(hours=7)
        datetime_to_date = datetime.combine(self.to_date, time.max) - timedelta(hours=7)
        all_product_ids = lines.mapped('product_id.id')
        domain = [
            ("product_id", "in", all_product_ids), 
            ("create_date", ">=", datetime_from_date),
            ("create_date", "<=", datetime_to_date), 
            ("stock_move_id", "!=", False),
            ("stock_move_id.production_id", "=", False), 
            '|',
            ("stock_move_id.location_dest_id.usage", "in", ['inventory']),
            ("stock_move_id.location_id.usage", "in", ["customer"]),

        ]
        all_layers = ModelLayer.search(domain)
        layers_by_product = {}
        for layer in all_layers:
            layers_by_product.setdefault(layer.product_id.id, ModelLayer)
            layers_by_product[layer.product_id.id] |= layer

        lines.compute_ex_warehouse_price()
        for line in lines:
            self.update_value_layers(layers_by_product.get(line.product_id.id, ModelLayer), line.ex_warehouse_price)
        
        self._update_move_credit_debit_batch(all_layers)
        lines.compute_total_export()
        products_to_update = {line.product_id.id: line.ex_warehouse_price for line in lines if line.ex_warehouse_price > 0}
        self.env['ir.property']._set_multi('standard_price', 'product.product', products_to_update)

    def _get_priority_th1(self, product_ids):
        if not product_ids:
            return []

        datefrom, dateto = self._get_layer_date_range()
        query = """
            SELECT DISTINCT svl_raw.product_id
            FROM stock_valuation_layer svl
                JOIN stock_move sm          ON sm.id = svl.stock_move_id
                JOIN stock_location sl_src  ON sl_src.id = sm.location_id
                JOIN mrp_production mp      ON mp.id = sm.production_id AND (mp.is_remanufacturing_order = FALSE OR mp.is_remanufacturing_order IS NULL)
                JOIN stock_move sm_raw      ON sm_raw.raw_material_production_id = mp.id
                JOIN stock_valuation_layer svl_raw ON svl_raw.stock_move_id = sm_raw.id
            WHERE svl.product_id = ANY(%s)
              AND svl.create_date >= %s
              AND svl.create_date <= %s
              AND sl_src.usage = 'production'
              AND svl.quantity > 0
        """
        self.env.cr.execute(query, (product_ids, datefrom, dateto))
        return [row[0] for row in self.env.cr.fetchall()]

    def _update_layer_finished_th1(self, lines, level):
        filtered_lines = lines.filtered(lambda x: x.quantity_in_period > 0)
        if not filtered_lines:
            return

        ModelLayer = self.env["stock.valuation.layer"]
        datetime_from_date = datetime.combine(self.from_date, time.min) - timedelta(hours=7)
        datetime_to_date = datetime.combine(self.to_date, time.max) - timedelta(hours=7)
        product_ids = filtered_lines.mapped('product_id.id')

        if self.apply_inventory:
            domain_loc = [("stock_move_id.location_id.usage", "in", ["production", "inventory"])]
        else:
            domain_loc = [("stock_move_id.location_id.usage", "in", ["production"])]

        domain2 = [
            ("quantity", '<', 0),
            ('stock_move_id.unbuild_id', '!=', False),
            ("stock_move_id.location_dest_id.usage", '=', 'production'),
        ]
        domain = expression.AND([
            expression.OR([domain_loc, domain2]),
            [
                ("product_id", "in", product_ids),
                ("create_date", ">=", datetime_from_date),
                ("create_date", "<=", datetime_to_date),
            ]
        ])
        if level in [2, 3]:
            domain = expression.AND([domain, [('stock_move_id.production_id.is_remanufacturing_order', '=', True)]])
        else:
            domain = expression.AND([domain, [
                '|',
                ('stock_move_id.production_id', '=', False),
                ('stock_move_id.production_id.is_remanufacturing_order', '=', False),
            ]])

        # 1 batch query thay vì N queries
        all_layers = ModelLayer.search(domain)
        layers_by_product = {}
        for layer in all_layers:
            layers_by_product.setdefault(layer.product_id.id, ModelLayer)
            layers_by_product[layer.product_id.id] |= layer

        for line in filtered_lines:
            layers = layers_by_product.get(line.product_id.id, ModelLayer)
            production_layer_ids = ModelLayer
            mo_layer_ids = {}
            value = 0
            for layer in layers:
                sm = layer.stock_move_id
                if sm.location_id.usage == 'production':
                    production_layer_ids |= sm.production_id.move_raw_ids.stock_valuation_layer_ids
                elif sm.location_id.usage == 'inventory':
                    value += layer.value
                elif sm.unbuild_id:
                    for mo in sm.unbuild_id.produce_line_ids.filtered(
                        lambda x: x.location_id.usage == 'production'
                    ).mapped("stock_valuation_layer_ids"):
                        mo_layer_ids.setdefault(mo, {'value': mo.value})

            # _logger.info(f"######## {line.product_id.default_code} Layers {self.id} value {value} - production_layer_ids: {production_layer_ids} - mo_layer_ids: {mo_layer_ids} - layers: {layers}")
            value_product_layer_ids = abs(sum(svl.value for svl in production_layer_ids))
            value += value_product_layer_ids
            value_unbuild = abs(sum(svl['value'] for svl in mo_layer_ids.values()))
            value -= value_unbuild
            if self.exclude_begin_period or self.is_finished_products:
                line.total_value_import = value
            else:
                line.total_value_import = value + line.initital_value
            line.value_621 = value_product_layer_ids - value_unbuild
            line.compute_actual_value()
            layers_prod = layers.filtered(lambda x: x.stock_move_id.location_id.usage == 'production')
            self.update_value_layers(layers_prod, line.value_per_unit)
            self._update_move_credit_debit_batch(layers_prod)
    
    def _update_layer_finished_th2(self, lines, level=0):
        if not lines:
            return
        ModelLayer = self.env["stock.valuation.layer"]
        datetime_from_date = datetime.combine(self.from_date, time.min) - timedelta(hours=7)
        datetime_to_date = datetime.combine(self.to_date, time.max) - timedelta(hours=7)
        all_layers = ModelLayer.search([
            ("product_id", "in", lines.mapped('product_id.id')),
            ("create_date", ">=", datetime_from_date),
            ("create_date", "<=", datetime_to_date),
            ("stock_move_id", "!=", False),
            ("stock_move_id.unbuild_id", "!=", False),
            ("stock_move_id.location_dest_id.usage", "=", "production"),
        ])
        layers_by_product = {}
        for layer in all_layers:
            layers_by_product.setdefault(layer.product_id.id, ModelLayer)
            layers_by_product[layer.product_id.id] |= layer

        for line in lines:
            self.update_value_layers(layers_by_product.get(line.product_id.id, ModelLayer), line.ex_warehouse_price)
        
        self._update_move_credit_debit_batch(all_layers)
        lines.compute_total_export()

    def _update_layer_finished_th3(self, lines, level=0):
        # TH3
        if not lines:
            return
        ModelLayer = self.env["stock.valuation.layer"]
        datetime_from_date = datetime.combine(self.from_date, time.min) - timedelta(hours=7)
        datetime_to_date = datetime.combine(self.to_date, time.max) - timedelta(hours=7)
        all_layers = ModelLayer.search([
            ("product_id", "in", lines.mapped('product_id.id')),
            ("create_date", ">=", datetime_from_date),
            ("create_date", "<=", datetime_to_date),
            ("stock_move_id", "!=", False),
            ("stock_move_id.production_id", "=", False),
            ("stock_move_id.location_dest_id.usage", "in", ["production"]),
        ])
        layers_by_product = {}
        for layer in all_layers:
            layers_by_product.setdefault(layer.product_id.id, ModelLayer)
            layers_by_product[layer.product_id.id] |= layer
        for line in lines:
            self.update_value_layers(layers_by_product.get(line.product_id.id, ModelLayer), line.ex_warehouse_price)
        
        self._update_move_credit_debit_batch(all_layers)
        lines.compute_total_export()

    def _update_layer_finished_th4(self, lines, level=0):
        # TH4
        if not lines:
            return
        ModelLayer = self.env["stock.valuation.layer"]
        datetime_from_date = datetime.combine(self.from_date, time.min) - timedelta(hours=7)
        datetime_to_date = datetime.combine(self.to_date, time.max) - timedelta(hours=7)
        all_layers = ModelLayer.search([
            ("product_id", "in", lines.mapped('product_id.id')),
            ("create_date", ">=", datetime_from_date),
            ("create_date", "<=", datetime_to_date),
            ("stock_move_id", "!=", False),
            ("stock_move_id.production_id", "=", False),
            '|',
            ("stock_move_id.location_dest_id.usage", "in", ["customer", 'inventory']),
            ("stock_move_id.location_id.usage", "in", ["customer"]),
        ])
        layers_by_product = {}
        for layer in all_layers:
            layers_by_product.setdefault(layer.product_id.id, ModelLayer)
            layers_by_product[layer.product_id.id] |= layer
        for line in lines:
            self.update_value_layers(layers_by_product.get(line.product_id.id, ModelLayer), line.ex_warehouse_price)

        self._update_move_credit_debit_batch(all_layers)
        lines.compute_total_export()

        products_to_update = {line.product_id.id: line.ex_warehouse_price for line in lines if line.ex_warehouse_price > 0}
        self.env['ir.property']._set_multi('standard_price', 'product.product', products_to_update)

    def update_value_layers(self, layers, value):
        self.env.cr.execute("""
            UPDATE stock_valuation_layer
            SET unit_cost = %s,
                value = %s * quantity,
                write_date = %s
            WHERE id = ANY(%s)
        """, (value, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), layers.ids))
        layers.invalidate_recordset(['unit_cost', 'value'])

        move_price_map = {r.stock_move_id.id: r.unit_cost for r in layers if r.stock_move_id}
        if move_price_map:
            values = ','.join(
                self.env.cr.mogrify('(%s,%s)', item).decode()
                for item in move_price_map.items()
            )
            self.env.cr.execute("""
                UPDATE stock_move SET price_unit = v.price
                FROM (VALUES %s) AS v(id, price)
                WHERE stock_move.id = v.id
            """ % values)

    def _update_move_credit_debit_batch(self, layers):
        layers_no_move = layers.env['stock.valuation.layer']
        layers_to_recreate = layers.env['stock.valuation.layer']

        for layer in layers:
            move = layer.account_move_id
            value = abs(layer.value)
            if not move:
                layers_no_move |= layer
                continue
            if len(move.line_ids) != 2:
                continue
            if all(line.balance == 0 for line in move.line_ids):
                layers_to_recreate |= layer
                continue
            to_write = []
            for line in move.line_ids:
                to_write.append((1, line.id, {
                    'debit': line.debit > 0.0 and value or 0.0,
                    'credit': line.credit > 0.0 and value or 0.0,
                }))
            move.write({'line_ids': to_write})

        moves_to_cancel = layers_to_recreate.mapped('account_move_id').filtered(lambda m: m.state == 'posted')
        if moves_to_cancel:
            moves_to_cancel.button_cancel()
            moves_to_cancel.unlink()

        for layer in layers_no_move | layers_to_recreate:
            date = layer.create_date + timedelta(hours=7)
            layer.with_context(force_period_date=date)._validate_accounting_entries()
        
    def action_general_end_cost(self):
        self.end_cost_allocation_ids.unlink()
        cost_ids = self.env['cost.allocation'].search([('account_consolidated_ids', '!=', False)])
        for cost in cost_ids:
            move_lines = self.env['account.move.line'].search([
                ('account_id', 'in', cost.account_consolidated_ids.ids),
                ('date', '>=', self.from_date),
                ('date', '<=', self.to_date),
                ('move_id.state', '=', 'posted'),
                ('move_id.carryover_mass_period_ids', '=', False)
            ])
            value = sum(move_lines.mapped('debit')) - sum(move_lines.mapped('credit'))
            self.env['end.period.cost.allocation'].create({
                'cost_id': cost.id,
                'total_cost': abs(value),
                'mass_period_id': self.id
            })

    def auto_carryover(self):
        if not self.end_cost_allocation_ids:
            return

        if any(not line.cost_id.account_consolidated_ids for line in self.end_cost_allocation_ids):
            return

        if self.carryover_move_id:
            self.carryover_move_id.button_cancel()
            self.carryover_move_id.unlink()

        default_balance = 0
        line_extra = []
        for acc in self.default_carryover_account_ids:
            move_lines = self.env['account.move.line'].search([
                ('account_id', '=', acc.id),
                ('date', '>=', self.from_date),
                ('date', '<=', self.to_date),
                ('move_id.state', '=', 'posted')
            ])   
            balance = sum(move_lines.mapped('debit')) - sum(move_lines.mapped('credit'))
            line_extra += [(0,0, {
                'account_id': acc.id,
                'debit': 0,
                'credit': round(balance),
            })]
            default_balance += round(balance)

        journal_entry_vals = {
            'journal_id': self.carryover_journal_id.id,  # Assuming the journal is linked to the mass period
            'date': self.to_date,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'account_id': self.carryover_debit_account_id.id,
                    'debit': sum(round(line.value) for line in self.end_cost_allocation_ids) + default_balance,
                    'credit': 0.0,
                })] + [
                (0, 0, {
                    'account_id': line.cost_id.account_consolidated_ids[0].id,
                    'debit': 0.0,
                    'credit': round(line.value),
                }) for line in self.end_cost_allocation_ids] + line_extra,
        }
        carryover_move_id = self.env['account.move'].create(journal_entry_vals)
        carryover_move_id.action_post()
        # account_sequence._set_next_sequence() flushes the move's name field only,
        # leaving move_name on lines pending in the recompute queue. In a loop context
        # the next DB read auto-flushes it, but here we return immediately so it never
        # flushes within the same transaction before callers read move_name.
        self.env.add_to_compute(
            self.env['account.move.line']._fields['move_name'],
            carryover_move_id.line_ids
        )
        self.env['account.move.line'].recompute()
        self.carryover_move_id = carryover_move_id.id
        return

    def action_carryover(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Carryover'),
            'res_model': 'account.selection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_mass_period_id': self.id,
            },
        }
