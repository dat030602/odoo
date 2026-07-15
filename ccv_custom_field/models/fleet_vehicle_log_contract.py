from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class FleetVehicleLogContract(models.Model):
    _inherit = "fleet.vehicle.log.contract"

    km_start = fields.Char(string="Km bắt đầu")
    km_end = fields.Char(string="Km kết thúc")

    # Thay Many2many bằng One2many
    product_note_ids = fields.One2many(
        'fleet.product.note',
        'contract_id',
        string="Sản phẩm"
    )

    amount_untax_total = fields.Monetary("Tổng chưa thuế", compute="_compute_total_amounts", store=True)
    amount_tax_total = fields.Monetary("Tổng thuế", compute="_compute_total_amounts", store=True)
    amount_total = fields.Monetary("Tổng cộng", compute="_compute_total_amounts", store=True)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id.id)
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)

    @api.depends('product_note_ids.amount_untax', 'product_note_ids.amount_tax', 'product_note_ids.amount_total')
    def _compute_total_amounts(self):
        for rec in self.sudo():
            rec.amount_untax_total = sum(rec.product_note_ids.mapped('amount_untax'))
            rec.amount_tax_total = sum(rec.product_note_ids.mapped('amount_tax'))
            rec.amount_total = sum(rec.product_note_ids.mapped('amount_total'))

    @api.depends_context('lang')
    @api.depends('product_note_ids.tax_id', 'product_note_ids.price_unit', 'amount_total', 'amount_untax_total', 'currency_id')
    def _compute_tax_totals(self):
        for rec in self:
            lines = rec.product_note_ids
            rec.tax_totals = rec.env['account.tax'].sudo()._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in lines],
                rec.currency_id or rec.company_id.currency_id,
            )
