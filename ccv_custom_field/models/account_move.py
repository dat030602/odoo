from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    restrict_mode_hash_table = fields.Boolean(
        related="journal_id.ccv_restrict_mode_hash_table"
    )
    # sale_id = fields.Many2one("sale.order", string="Đơn bán hàng", copy=False)

    def button_draft(self):
        super(AccountMove, self).button_draft()
        self.write({"posted_before": False})

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self:
            if move.move_type != 'out_invoice':
                continue
            if move.sinvoice_count > 0:
                continue
            sale_orders = move.invoice_line_ids.mapped('sale_line_ids.order_id')
            has_done_picking = any(
                p.state == 'done'
                for so in sale_orders
                for p in so.picking_ids
            )
            if has_done_picking:
                try:
                    move.sudo().action_create_data_sinvoice()
                    _logger.info("Đã tạo S-Invoice cho invoice %s sau khi post", move.name)
                except Exception as e:
                    _logger.error("Không thể tạo S-Invoice cho %s: %s", move.name, e, exc_info=True)
        return res

    # def action_post(self):
    #     for line in self.invoice_line_ids:
    #         line._update_income_svl_transfer()
    #     res = super(AccountMove, self).action_post()
    #     return res

    # @api.onchange("sale_id")
    # def _onchange_sale_ids(self):
    #     for rec in self:
    #         rec.sale_id = False
    #         if rec.sale_id:
    #             account_move = rec
    #             order = rec.sale_id
    #             sale_order_lines = order.order_line
    #             invoice_lines = account_move.invoice_line_ids
    #             for sale_line, invoice_line in zip(sale_order_lines, invoice_lines):
    #                 invoice_line.write({"sale_line_ids": [(4, sale_line.id)]})

    def create_data_sinvoice(self):
        partner_vat = self.partner_vat_id and self.partner_vat_id or self.partner_id
        val_sinvoice = {
            "invoice_id": self.id,
            "company_id": self.company_id.id,
            "name": self.name,
            "currency_id": self.currency_id.id,
            "partner_vat_id": self.partner_vat_id and self.partner_vat_id.id or self.partner_id.id,
            "date_invoice": self.invoice_date,
            "date": self.date,
            "company_currency_id": self.company_currency_id.id,
            "type": self.move_type,
            "journal_id": self.journal_id.id,
            "fiscal_position_id": self.fiscal_position_id and self.fiscal_position_id.id,
            'partner_vat': partner_vat.vat,
            'partner_vat_address': partner_vat.address_invoice_vat or self.get_partner_address(partner_vat),
            'partner_vat_name': partner_vat.name_vat,
            'use_identity_card': partner_vat.use_identity_card,
            'partner_identity_card': partner_vat.identity_card,
        }
        sinvoice_id = self.env['viettel.sinvoice'].create(val_sinvoice)
        if sinvoice_id:
            data_obj = self.env['viettel.sinvoice.data']
            for line in self.invoice_line_ids:
                sale_line_id = line.sale_line_ids or False
                vals = sinvoice_id.create_data_sinvoice_line(line, sale_line_id=sale_line_id)
                for val in vals:
                    data_obj.create(val)
        return True 
