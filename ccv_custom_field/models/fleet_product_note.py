from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class FleetProductNote(models.Model):
    _name = "fleet.product.note"
    _description = "Fleet Product Note"

    name = fields.Char("Tên")
    product_id = fields.Many2one("product.product", "Sản phẩm")
    price_unit = fields.Monetary("Đơn giá", required=True)
    quantity = fields.Float("Số lượng", default=1.0, digits='Product Unit of Measure')
    uom_id = fields.Many2one("uom.uom", string="Đơn vị tính")  # <-- Thêm dòng này

    amount_untax = fields.Monetary("Giá chưa thuế", compute="_compute_amounts", store=True)
    amount_tax = fields.Monetary("Tiền thuế", compute="_compute_amounts", store=True)
    amount_total = fields.Monetary("Thành tiền", compute="_compute_amounts", store=True)
    tax_id = fields.Many2one("account.tax", "Thuế")
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id.id)

    contract_id = fields.Many2one("fleet.vehicle.log.contract", string="Hợp đồng")
    log_service_id = fields.Many2one("fleet.vehicle.log.services", string="Dịch vụ")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                rec.uom_id = rec.product_id.uom_id

    @api.depends('price_unit', 'quantity', 'tax_id')
    def _compute_amounts(self):
        for rec in self.sudo():
            subtotal = rec.price_unit * rec.quantity
            rec.amount_untax = subtotal
            if rec.tax_id:
                taxes = rec.tax_id.compute_all(rec.price_unit, rec.currency_id, rec.quantity, product=rec.product_id)
                rec.amount_tax = taxes['total_included'] - taxes['total_excluded']
                rec.amount_total = taxes['total_included']
            else:
                rec.amount_tax = 0.0
                rec.amount_total = subtotal

    def _convert_to_tax_base_line_dict(self):
        self.ensure_one()
        return self.env['account.tax'].sudo()._convert_to_tax_base_line_dict(
            self,
            currency=self.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            quantity=self.quantity,
            price_subtotal=self.amount_total,
        )
