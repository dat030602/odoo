from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class ApprovalProductLine(models.Model):
    _inherit = 'approval.product.line'

    qty_norm_25kg = fields.Float(string="Sản lượng 25kg", digits="Product Unit of Measure", compute="_compute_qty_norm", store=True)
    qty_norm_50kg = fields.Float(string="Sản lượng 50kg", digits="Product Unit of Measure", compute="_compute_qty_norm", store=True)
    
    qty_km_vehicle = fields.Float(string="Số giờ")
    qty_km_vehicle_pre = fields.Float(string="Số giờ trước")
    qty_norm_fuel = fields.Float(string="Tổng lượng xăng dầu", compute="_compute_qty_norm_fuel", store=True)

    pre_bom_qty = fields.Float(string="Số lượng đề xuất trước", digits="Product Unit of Measure", compute="_compute_qty_norm", store=True)
    over_bom_qty = fields.Float(string="Vượt định mức bao", digits="Product Unit of Measure", compute="_compute_qty_norm", store=True)
    product_over_bom_id = fields.Many2one(string="BOM vượt định mức sản phẩm", comodel_name="approval.bom.product", compute="_compute_qty_norm", store=True)
    price_over_bom = fields.Monetary(string="Số tiền vượt định mức", currency_field="currency_id", compute="_compute_qty_norm", store=True)
    
    over_bom_qty_fuel = fields.Float(string="Vượt định mức xăng dầu", digits="Product Unit of Measure", compute="_compute_qty_norm_fuel", store=True)
    product_over_bom_fuel_id = fields.Many2one(string="Vượt định mức xăng dầu", comodel_name="approval.bom.product", compute="_compute_qty_norm_fuel", store=True)
    price_over_bom_fuel = fields.Monetary(string="Số tiền vượt định mức", currency_field="currency_id", compute="_compute_qty_norm_fuel", store=True)

    currency_id = fields.Many2one(string="Tiền tệ", comodel_name="res.currency", default=lambda self: self.env.company.currency_id)

    @api.constrains('qty_km_vehicle')
    def _check_qty_km_vehicle(self):
        for record in self:
            if record.approval_request_id and record.approval_request_id.date and record.approval_request_id.category_id.has_fuel_norm == 'optional' and record.qty_km_vehicle <= 0:
                raise ValidationError("Số giờ không được bằng 0 !!!")
    
    @api.depends('product_id','approval_request_id.date','approval_request_id.department_id','approval_request_id.category_id.has_count_norm')
    def _compute_qty_norm(self):
        """
        Compute normalized quantities for 25kg and 50kg bags based on production history
        since the last approved request for the same product and department.
        """
        for record in self.sudo():
            record.qty_norm_25kg = 0.0
            record.qty_norm_50kg = 0.0

            # Only compute when sewing norm is enabled on category
            if not record.approval_request_id or record.approval_request_id.category_id.has_count_norm == 'no':
                continue
            
            if not record.product_id:
                continue
                
            bom_product = record._get_bom_product(record.product_id)
            if not bom_product:
                continue
                
            last_approved_request = record._get_last_approved_request(record)
            if not last_approved_request:
                continue
                
            start_date = record._get_start_date_from_last_request(last_approved_request)
            if not start_date:
                continue
                
            # Use current approval's date as the end datetime
            end_datetime = record.approval_request_id.date
            if not end_datetime:
                continue
            
            production_records = record._get_production_records(start_date, end_datetime, record.approval_request_id.department_id)
            
            qty_25kg, qty_50kg, pre_qty, over_bom_qty = record._calculate_normalized_quantities(production_records, bom_product, last_approved_request)
            
            record.qty_norm_25kg = qty_25kg
            record.qty_norm_50kg = qty_50kg
            record.pre_bom_qty = pre_qty
            record.over_bom_qty = over_bom_qty
            record.price_over_bom = bom_product.price_unit * over_bom_qty
            record.product_over_bom_id = bom_product

    def _get_bom_product(self, product):
        """Get BOM product configuration for the given product."""
        return self.env['approval.bom.product'].search([('product_id', '=', product.id)], limit=1)

    def _get_last_approved_request(self, record):
        """Get the last approved request for the same product and department.

        Avoid comparing against transient NewId values during onchange by only
        excluding the current request if it has a persisted database ID.
        """
        ApprovalRequest = self.env['approval.request'].sudo()
        domain = [
            ('category_id', '=', record.approval_request_id.category_id.id),
            ('product_line_ids.product_id', '=', record.product_id.id),
            ('department_id', '=', record.approval_request_id.department_id.id),
            ('request_status', '=', 'approved'),
        ]
        # When computing fuel norms, also constrain by partner if available
        if getattr(record, 'partner_id', False) and record.partner_id:
            domain.append(('product_line_ids.partner_id', '=', record.partner_id.id))

        # Exclude current request only if it exists in DB
        current_id = record.approval_request_id and record.approval_request_id._origin.id
        if current_id:
            domain.append(('id', '!=', current_id))

        approved_requests = ApprovalRequest.search(domain, order='date desc')
        
        if not approved_requests:
            return None
            
        # Filter out requests from the same date as current request
        different_date_requests = approved_requests.filtered(lambda r: r.date.date() != record.approval_request_id.date.date())
        
        if not different_date_requests:
            return None
            
        # Get the most recent date
        max_date = max(req.date.date() for req in different_date_requests)
        
        # Return requests from the most recent date
        return different_date_requests.filtered(lambda r: r.date.date() == max_date)

    def _get_start_date_from_last_request(self, last_approved_requests):
        """Get the start date from the last approved requests."""
        if not last_approved_requests:
            return None
            
        return min(req.date.date() for req in last_approved_requests)

    def _get_production_records(self, start_date, end_datetime, department):
        """Get production records from start_date to end_datetime for the given department."""
        domain = [
            ('stock_date_receipt', '>=', start_date.strftime('%Y-%m-%d %H:%M:%S')),
            ('stock_date_receipt', '<=', end_datetime.strftime('%Y-%m-%d %H:%M:%S')),
            ('state', '=', 'done'),
            ('department_ids', 'in', [department.id]),
        ]
        
        return self.env['mrp.production'].sudo().search(domain)

    def _get_pre_data(self, product, last_approved_request):
        """Get pre data from the last approved request."""
        if not last_approved_request:
            return 0.0
        product_lines = last_approved_request.product_line_ids.filtered(lambda x: x.product_id == product)
        return sum(product_lines.mapped('quantity')) or 0.0

    def _calculate_normalized_quantities(self, production_records, bom_product, last_approved_request=False):
        """Calculate normalized quantities for 25kg and 50kg bags."""
        self.ensure_one()
        qty_25kg = 0.0
        qty_50kg = 0.0

        pre_qty = self._get_pre_data(self.product_id, last_approved_request)

        for production in production_records:
            if production.product_id.default_specification_id == bom_product.uom_25kg_id:
                qty_25kg += production.qty_produced
            elif production.product_id.default_specification_id == bom_product.uom_50kg_id:
                qty_50kg += production.qty_produced
        
        # Apply normalization factors safely (avoid division by zero)
        factor_25 = bom_product.qty_norm_25kg or 0.0
        factor_50 = bom_product.qty_norm_50kg or 0.0
        bom_qty_25kg = qty_25kg / (factor_25 or 1)
        bom_qty_50kg = qty_50kg / (factor_50 or 1)

        over_bom_qty = pre_qty - (bom_qty_25kg + bom_qty_50kg)
        return qty_25kg, qty_50kg, pre_qty, over_bom_qty if over_bom_qty > 0 else 0.0

    @api.depends('partner_id','product_id','qty_km_vehicle','approval_request_id.date','approval_request_id.department_id','approval_request_id.category_id.has_fuel_norm')
    def _compute_qty_norm_fuel(self):
        """
        Compute fuel norm by mapping product line partner to BOM partner
        and multiplying total produced quantity in the period by the BOM fuel norm.
        Period: from last approved request date (same product/department rules) to current approval's date.
        """
        for record in self.sudo():
            record.qty_norm_fuel = 0.0

            # Only compute when fuel norm is enabled on category
            if not record.approval_request_id or record.approval_request_id.category_id.has_fuel_norm == 'no':
                continue

            # Require partner and approval context
            if not record.partner_id or not record.approval_request_id or not record.approval_request_id.date or not record.approval_request_id.department_id:
                continue

            # Find BOM fuel config by partner and product
            bom_fuel = self.env['approval.bom.product'].search([
                ('partner_id', '=', record.partner_id.id),
                ('product_id', '=', record.product_id.id),
            ], limit=1)
            if not bom_fuel or not bom_fuel.qty_norm_fuel:
                continue

            # Find last approved requests (before current) using existing helper
            last_approved_requests = record._get_last_approved_request(record)

            # Get previous odometer from last approved request line with same product and partner
            previous_km = 0
            previous_quantity = 0
            if last_approved_requests:
                previous_line = self.env['approval.product.line'].sudo().search([
                    ('approval_request_id', 'in', last_approved_requests.ids),
                    ('product_id', '=', record.product_id.id),
                    ('partner_id', '=', record.partner_id.id),
                ], order='id desc', limit=1)
                if previous_line:
                    previous_km = previous_line.qty_km_vehicle or 0
                    previous_quantity = previous_line.quantity or 0

            current_km = record.qty_km_vehicle or 0
            delta_km = current_km - previous_km
            if delta_km < 0:
                delta_km = 0

            # Compute fuel consumption as delta kilometers times norm per km
            record.qty_norm_fuel = float(delta_km * bom_fuel.qty_norm_fuel) if delta_km > 0 else 0.0

            # Tính lượng vượt định mức: Lấy số lượng hiện tại TRỪ ĐI định mức cho phép
            qty_fuel_over = record.quantity - record.qty_norm_fuel
            record.over_bom_qty_fuel = qty_fuel_over if qty_fuel_over > 0 else 0.0

            record.price_over_bom_fuel = bom_fuel.price_unit * record.over_bom_qty_fuel
            record.product_over_bom_fuel_id = bom_fuel
            record.qty_km_vehicle_pre = previous_km
