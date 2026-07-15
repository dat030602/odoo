# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression
from datetime import timedelta, datetime, time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import json
import logging

_logger = logging.getLogger(__name__)

class CostAllocation(models.Model):
    _name = 'cost.allocation'
    _description = 'Cost allocation'

    name = fields.Char("Name", required=True)
    account_consolidated_ids = fields.Many2many("account.account", string="Accounts to be consolidated")
    
class EndPfPeriodCostAllocation(models.Model):
    _name = 'end.period.cost.allocation'
    _description = 'End of period cost allocation'

    mass_period_id = fields.Many2one("average.price.end.period.mass", string="Mass period", index=True)
    period_id = fields.Many2one("average.capital.price.end.period", string="Period", index=True,ondelete=False)
    cost_id = fields.Many2one("cost.allocation", 'Cost name')
    date = fields.Datetime("Date Incurred")
    total_cost = fields.Float("Total Allocation Cost")
    value = fields.Float("Value by Allocation Rate", compute="compute_value", store=False, readonly=False)
    note = fields.Text('Note')

    @api.depends("total_cost", 'mass_period_id.allocation_rate', 'period_id.allocation_rate', 'cost_id')
    def compute_value(self):
        for res in self:
            value = 0
            if res.period_id:
                mass_period_id = res.period_id.mass_period_id
                if mass_period_id:
                    sum_qty_import = sum(mass_period_id.period_ids.mapped('period_line_ids').mapped("total_quantity_import"))
                    a = sum_qty_import and mass_period_id.total_allocation_value / sum_qty_import or 0
                    sum_qty = sum(res.period_id.mapped('period_line_ids').mapped("total_quantity_import"))
                    value = a * sum_qty
                else:
                    value = res.total_cost * res.period_id.allocation_rate / 100
            elif res.mass_period_id:
                value = res.total_cost * res.mass_period_id.allocation_rate / 100
            res.value = value

class AverageCapitalPriceEndPeriod(models.Model):
    _name = "average.capital.price.end.period"
    _description = "Average Capital Price End Period"
    _order = 'from_date desc'

    def _product_ids_domain(self):
        return [("categ_id", "!=", False), ("categ_id.property_cost_method", "in", ["fifo", "average"])]

    mass_period_id = fields.Many2one("average.price.end.period.mass", string="Mass period", index=True)
    name = fields.Char(string="Char", compute="_compute_name", store=True)
    from_date = fields.Date(string="From Date", copy=False)
    to_date = fields.Date(string="To Date", copy=False)
    is_finished_products = fields.Boolean(string="+ Finished products have been manufactured", copy=False, default=False)
    previous_period_id = fields.Many2one(comodel_name="average.capital.price.end.period", string="Previous Period",
                                         copy=False)
    previous_period_ids = fields.Many2many(comodel_name="average.capital.price.end.period",
                                        relation='average_capital_price_end_period_prev_period_rel',  
                                        column1='average_capital_price_end_period_id',              
                                        column2='prev_period_id', string="Previous Period",copy=False)
    period_line_ids = fields.One2many(comodel_name="average.capital.price.end.period.line", inverse_name="period_id",
                                      string="Period Line", copy=False)
    product_ids = fields.Many2many(comodel_name="product.product",
                                   relation="average_capital_price_end_period_product_rel", column1="period_id",
                                   column2="product_id", domain=_product_ids_domain, string="Product", copy=False)

    allocation_rate = fields.Float("Allocation Rate")
    end_cost_allocation_ids = fields.One2many("end.period.cost.allocation",'period_id', 'Cost')

    total_allocation_value = fields.Float(string="Total value allocation cost", compute='compute_value')
    warehouse_id = fields.Many2one("stock.warehouse", 'Warehouse')
    stock_valuation_layer_ids = fields.One2many("stock.valuation.layer", 'average_period_id', 'Layers')
    account_move_ids = fields.One2many("account.move", 'average_period_id', 'Move')

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

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if self._context.get("filter_previous_period_id"):
            product_ids = self._context.get("filter_previous_period_id")[0][2]
            args = expression.AND([[("product_ids", 'in', product_ids)], args])
        if self._context.get("filter_period_id"):
            period_id = self._context.get("filter_period_id")
            args = expression.AND([[("id", '!=', period_id)], args])
        return super(AverageCapitalPriceEndPeriod, self)._name_search(name, args, operator, limit, name_get_uid)

    def fetch_data_layers_without_internal(self):
        datetime_from_date = datetime.combine(self.from_date, time.min) - timedelta(hours=7)
        datetime_to_date = datetime.combine(self.to_date, time.max) - timedelta(hours=7)
        datefrom = datetime_from_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        dateto = datetime_to_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        domain = """ and 
            (
                (la.quantity > 0 and sld.usage = 'supplier' and (sp.is_actual_return_with_invoice is null or sp.is_actual_return_with_invoice = False))
                or
                (la.quantity > 0 and sl.usage in ('supplier', 'inventory'))
                or 
                (la.quantity > 0 and sl.usage = 'production' and sm.unbuild_id is null)
                or
                (la.quantity < 0 and sl.usage in ('supplier','production'))
                or 
                (la.quantity < 0 and sld.usage = 'supplier' and (sp.is_actual_return_with_invoice is null or sp.is_actual_return_with_invoice = False))
                or
                (la.quantity < 0 and sld.usage = 'production' and sm.unbuild_id is not null)
            )
        """
        if not self.mass_period_id.apply_inventory:
            domain = """ and 
                (
                    (la.quantity > 0 and sld.usage = 'supplier' and (sp.is_actual_return_with_invoice is null or sp.is_actual_return_with_invoice = False))
                    or
                    (la.quantity > 0 and sl.usage = 'supplier')
                    or 
                    (la.quantity > 0 and sl.usage = 'production' and sm.unbuild_id is null)
                    or
                    (la.quantity < 0 and sl.usage in ('supplier','production'))
                    or 
                    (la.quantity < 0 and sld.usage = 'supplier' and (sp.is_actual_return_with_invoice is null or sp.is_actual_return_with_invoice = False))
                    or
                    (la.quantity < 0 and sld.usage = 'production' and sm.unbuild_id is not null)
                )
            """

        query = """
            select distinct(la.id)
            from stock_valuation_layer la 
                join stock_move sm on sm.id = la.stock_move_id
                left join stock_move_line sml on sm.id = sml.move_id
                left join stock_picking sp on sp.id = sml.picking_id
                left join stock_location sl on sl.id = sml.location_id
                left join stock_location sld on sld.id = sml.location_dest_id
            where la.create_date >= '{datefrom}' 
                and la.create_date <= '{dateto}'
                {domain}
                and la.product_id in %s

        """.format(datefrom=datefrom, dateto=dateto, domain=domain) 

        self._cr.execute(query, (tuple(self.product_ids.ids),))
        results = self._cr.dictfetchall()
        data = {}
        for result in results:
            layer = self.env['stock.valuation.layer'].browse(result['id'])
            if layer.stock_move_id and layer.stock_move_id.production_id and layer.stock_move_id.production_id.is_remanufacturing_order:
                continue
            
            rs = data.setdefault(layer.product_id.id, {
                'layers' : []
            })
            rs['layers'].append(layer.id)
        return data	

    def fetch_data_allocated(self):
        domain = [
            ('date','>=', self.from_date),
            ('date','<=', self.to_date),
        ]
        allocated = self.env['costs.allocated.directly.items'].search(domain)
        products = {}
        for al in allocated:
            for line in al.enter_cost_ids:
                res = products.setdefault(line.product_id, {
                    'total': 0 
                })
                res['total'] += line.allocation_cost

        return products

    def action_pricing(self):
        vals_list = []
        data_import_without_internal = self.fetch_data_layers_without_internal()
        data_allocated = self.fetch_data_allocated()

        for prod in self.product_ids:
            initital_value = initital_quantity = 0

            if self.previous_period_ids:
                is_finished_products = self.mass_period_id.is_finished_products or self.mass_period_id.exclude_begin_period

                previous_product = self.previous_period_ids.filtered(lambda x: x.period_line_ids).mapped('period_line_ids').filtered(lambda y: y.product_id.id == prod.id)
                initital_quantity = sum(previous_product.mapped("total_quantity_import")) 
                if is_finished_products:
                    initital_quantity += sum(previous_product.mapped("initital_quantity"))

                if initital_quantity:
                    initital_value = sum(previous_product.mapped("actual_value_import")) 
                    if is_finished_products:
                        initital_value += sum(previous_product.mapped("initital_value")) 
                    
                initital_quantity -= abs(sum(previous_product.mapped("total_quantity_export")))
                initital_value -= abs(sum(previous_product.mapped("total_value_export")))
            
            layer_import = data_import_without_internal.get(prod.id, {}) or {}
            allocation_cost = data_allocated.get(prod, False)
            total_cost = allocation_cost and allocation_cost['total'] or 0
            
            vals_list.append({
                "product_id": prod.id,
                "initital_quantity": abs(initital_quantity),
                "initital_value": abs(initital_value),
                'allocation_cost': total_cost,
                "period_id": self.id,
                'stock_valuation_layer_ids': [(6,0, layer_import.get('layers',[]))],
                'allocation_details_by_account_ids': [(0, 0, {
                    'account_ids': [(6, 0, line.cost_id.account_consolidated_ids.ids)],
                    'end_period_cost_allocation_id': line.id,
                }) for line in self.mass_period_id.end_cost_allocation_ids]
            })

        self.period_line_ids.unlink()
        self.period_line_ids.create(vals_list)
        return

    def update_initial_layer_cost(self):
        domain_layer = [
            ('create_date','>=', self.from_date),	
            ('create_date','<=', self.to_date),
            ('location_id.usage','=', 'supplier'),
            ('stock_move_id.purchase_line_id','!=', False),
        ]
        layers = self.env['stock.valuation.layer'].search(domain_layer)
        for layer in layers:
            move_id = layer.stock_move_id
            if move_id.price_unit != layer.unit_cost:
                layer.write({
                    'unit_cost': move_id.price_unit,
                    'value': layer.quantity * move_id.price_unit,
                })

    def _fetch_query_data_move(self):
        datetime_from_date = datetime.combine(self.from_date, time.min) - timedelta(hours=7)
        datetime_to_date = datetime.combine(self.to_date, time.max) - timedelta(hours=7)

        query = """
            select ml.id, ml.product_id
            from stock_move_line ml
                join stock_location sl on sl.id = ml.location_id
                join stock_location sld on sld.id = ml.location_dest_id
            where ml.date >= %s and ml.date <= %s
            and sl.warehouse_id != sld.warehouse_id
            and sl.usage = 'internal'
            and sld.usage = 'internal'
            and ml.state = 'done'
            and ml.product_id = ANY(%s)    -- ← thêm filter này
        """

        self._cr.execute(query, (datetime_from_date, datetime_to_date, list(self.product_ids.ids)))
        results = self._cr.dictfetchall()
        data = {}
        for result in results:
            res = data.setdefault(result['product_id'], {
                'move_lines': []
            })
            res['move_lines'].append(result['id'])
        
        return data

    def update_internal_transfer_price(self):
        data_move = self._fetch_query_data_move()
        for line in self.period_line_ids:
            product_data = data_move.get(line.product_id.id, False)
            if not product_data:
                continue

            move_lines = self.env['stock.move.line'].browse(product_data['move_lines'])
            for ml in move_lines:
                ml.write({
                    'internal_transfer_price': line.ex_warehouse_price
                })
                for layer in ml.internal_transfer_layer_ids:
                    layer.write({
                        'unit_cost': line.ex_warehouse_price,
                        'value': layer.quantity * line.ex_warehouse_price,
                        'average_period_id': self.id,
                    })
                    if layer.quantity > 0:
                        if not layer.interval_move_id:
                            move = self.create_move_internal_transfer_price(ml, layer)
                            move.action_post()
                            layer.interval_move_id = move.id
                        else:
                            to_write = []
                            for moveline in layer.interval_move_id.line_ids:
                                to_write.append((1, moveline.id, {
                                    'debit': moveline.debit > 0.0 and layer.value or 0.0,
                                    'credit': moveline.credit > 0.0 and layer.value or 0.0,
                                }))
                            layer.interval_move_id.write({'line_ids': to_write})
    
    def create_move_internal_transfer_price(self, ml, svl1):
        description = "Expenses %s" % (ml.product_id.name)
        credit_acc = ml.product_id.categ_id.property_stock_valuation_account_id
        debit_acc = ml.product_id.categ_id.property_stock_valuation_account_id
        accounts = ml.product_id.product_tmpl_id.get_product_accounts()

        move_lines = ml.move_id._prepare_account_move_line(svl1.quantity, svl1.value, credit_acc.id, debit_acc.id, svl1.id, description)
        return self.env['account.move'].create({
            'journal_id': accounts['stock_journal'].id,
            'line_ids': move_lines,
            'date': ml.date,
            'ref': description,
            'stock_move_id': ml.move_id.id,
            'move_type': 'entry',
            'average_period_id': self.id
        })

class AverageCapitalPriceEndPeriodLine(models.Model):
    _name = "average.capital.price.end.period.line"
    _description = "Average Capital Price End Period Line"

    period_id = fields.Many2one("average.capital.price.end.period", string="Period", ondelete='cascade', index=True)
    product_id = fields.Many2one(comodel_name="product.product", string="Product", copy=False)
    initital_quantity = fields.Float(string="Initial Quantity", digits='Product Unit of Measure', copy=False)
    initital_value = fields.Float(string="Initial Value", copy=False)
    total_quantity_import = fields.Float(string="Total quantity import", 
                                         digits='Product Unit of Measure', copy=False, compute="compute_total", store=True)
    
    total_value_import = fields.Float(string="Total value import", 
                                      copy=False, compute="compute_total", store=True)
    
    actual_value_import = fields.Float("Total Value Import", copy=False)

    value_per_unit = fields.Float(string="Value/1 unit", copy=False, compute='compute_value_per_unit', store=True)
    quantity_in_period = fields.Float(string="Quantity in the period",copy=False, compute="compute_layers_all", store=True)
    unit_value = fields.Float(string="Unit Value", copy=False, compute="compute_layers_all", store=True)
    allocation_cost = fields.Float("Allocation cost")
    is_internal = fields.Boolean("Is Internal", copy=False)
    stock_valuation_layer_ids = fields.Many2many("stock.valuation.layer", string="Stock Valuation Layer")
    allocation_details_by_account_ids = fields.One2many("allocation.details.by.account", 'period_line_id', 'Allocation Details By Account')
    value_621 = fields.Float(string='621 Value')
    ex_warehouse_price = fields.Float(string="Ex-warehouse Price")
    total_quantity_export = fields.Float(string="Total quantity export")
    total_value_export = fields.Float(string="Total value export")

    def compute_total_export(self):
        for res in self:
            datetime_from_date = datetime.combine(res.period_id.mass_period_id.from_date, time.min) - timedelta(hours=7)
            datetime_to_date = datetime.combine(res.period_id.mass_period_id.to_date, time.max) - timedelta(hours=7)
            datefrom = datetime_from_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            dateto = datetime_to_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

            query = f"""
                select distinct(la.id)
                from stock_valuation_layer la 
                    join stock_move sm on sm.id = la.stock_move_id
                    left join stock_move_line sml on sm.id = sml.move_id
                    left join stock_picking sp on sp.id = sml.picking_id
                    left join stock_location sl on sl.id = sml.location_id
                    left join stock_location sld on sld.id = sml.location_dest_id
                where la.create_date >= '{datefrom}' 
                    and la.create_date <= '{dateto}'
                    and sld.usage in ('supplier', 'customer','inventory')
                    and sl.usage not in ('supplier', 'customer','inventory')
                    and la.product_id = {res.product_id.id}
            """ 

            self._cr.execute(query)
            results = self._cr.dictfetchall()

            stock_valuation_layer_ids = self.env['stock.valuation.layer'].browse([r['id'] for r in results])
            res.total_quantity_export = sum(stock_valuation_layer_ids.mapped('quantity'))
            res.total_value_export = sum(stock_valuation_layer_ids.mapped('value'))

    def compute_ex_warehouse_price(self):
        for res in self:
            is_finished_products = res.period_id.mass_period_id.is_finished_products or res.period_id.mass_period_id.exclude_begin_period
            d = res.total_quantity_import
            if is_finished_products:
                d = res.total_quantity_import + res.initital_quantity
            
            res.ex_warehouse_price = ((res.value_per_unit  * res.quantity_in_period) + res.initital_value)/ d if d else 0

    @api.depends("stock_valuation_layer_ids")
    def compute_layers_all(self, is_th1=False):
        for res in self:
            layers = res.stock_valuation_layer_ids
            if is_th1:
                layers = layers.filtered(lambda x: not x.stock_move_id.production_id or not x.stock_move_id.production_id.is_remanufacturing_order)
            
            res.quantity_in_period = sum(layers.mapped('quantity'))
            res.unit_value = sum(layers.mapped('value'))

    @api.depends('initital_quantity', 'initital_value','quantity_in_period', 'unit_value')
    def compute_total(self):
        for res in self:
            is_finished_products = res.period_id.mass_period_id.is_finished_products or res.period_id.mass_period_id.exclude_begin_period
            res.total_quantity_import = res.quantity_in_period + (res.initital_quantity if not is_finished_products else 0)
            res.total_value_import = res.unit_value + (res.initital_value if not is_finished_products else 0)

    def compute_actual_value(self):
        mass_data = {}
        for res in self:
            a = 0
            mp = res.period_id.mass_period_id
            allocation_cost = 0
            if mp:
                if mp.id not in mass_data:
                    mass_data[mp.id] = {
                        'data_quantity_import': json.loads(mp.data_quantity_import or '{}'),
                        'sum_quantity_import': mp.sum_quantity_import,
                        'total_allocation_value': mp.total_allocation_value,
                    }
                
                data_quantity_import = mass_data[mp.id]['data_quantity_import']
                sum_qty_import = mass_data[mp.id]['sum_quantity_import']
                a = sum_qty_import and mass_data[mp.id]['total_allocation_value'] / sum_qty_import or 0
                sum_qty_prod = data_quantity_import.get(str(res.product_id.id), {})
                allocation_cost = sum_qty_prod and res.allocation_cost / sum_qty_prod or 0 
            
            # Calculate actual value import
            actual_value = res.total_value_import + (a * res.quantity_in_period) + (allocation_cost * res.quantity_in_period)
            res.actual_value_import = round(actual_value, 0)

    @api.depends("total_quantity_import", 'actual_value_import')
    def compute_value_per_unit(self):
        for res in self:
            res.value_per_unit = round(res.actual_value_import / res.total_quantity_import, 0) if res.total_quantity_import else 0
                
    def copy(self, default=None):
        default = default or {}
        res = super().copy(default)
        res.allocation_details_by_account_ids = [(0, 0, detail.copy_data()[0]) for detail in self.allocation_details_by_account_ids]
        return res