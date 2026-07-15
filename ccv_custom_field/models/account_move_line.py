from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    # Ảnh sản phẩm
    products_image_512 = fields.Image(
        string="Hình ảnh sản phẩm",
        compute="_compute_product_image_512",
        inverse="_inverse_product_image_512",
        store=True,
        max_width=512,
        max_height=512
    )

    products_image_128 = fields.Image(
        string="Hình ảnh sản phẩm",
        compute="_compute_product_image_128",
        inverse="_inverse_product_image_128",
        store=True,
        max_width=128,
        max_height=128
    )

    # Compute & Inverse cho product_image
    @api.depends('products_image')
    def _compute_product_image_512(self):
        for rec in self:
            rec.products_image_512 = rec.products_image

    def _inverse_product_image_512(self):
        for rec in self:
            rec.products_image = rec.products_image_512

    @api.depends('products_image')
    def _compute_product_image_128(self):
        for rec in self:
            rec.products_image_128 = rec.products_image

    def _inverse_product_image_128(self):
        for rec in self:
            rec.products_image = rec.products_image_128
    
    @api.onchange('product_id')
    def compute_new_image(self):
        for image_id in self:
            image_id.products_image = None
            for for_image in image_id.product_id:
                image_id.products_image = for_image.image_512

    def _update_income_svl_transfer(self):
        purchase_line_id = self.purchase_line_id.sudo()
        # move_ids = purchase_line_id.move_ids
        move_ids = purchase_line_id.order_id.picking_ids.mapped('move_ids').filtered(lambda l:l.product_id == self.product_id)
        if not purchase_line_id or not move_ids:
            return
        
        rate = 1
        if purchase_line_id.order_id.apply_manual_currency_exchange:
            rate = purchase_line_id.order_id.inverse_manural_currency_exchange_rate
        price_unit = self.price_unit * rate
        
        if price_unit == 0:
            return
        
        for move_id in move_ids:
            svl_ids = move_id.stock_valuation_layer_ids
            new_price_unit = price_unit
            new_price_unit *= self.product_uom_id.factor / move_id.product_uom.factor
            for svl in svl_ids.filtered(lambda l:l.unit_cost != new_price_unit or l.account_move_id is False):
                value = new_price_unit * svl.quantity
                svl.with_user(1).write({'unit_cost': new_price_unit, 'value': value})
                account_move_id = svl.account_move_id
                # move = svl.stock_move_id

                # account_id = move.account_id
                # account_dest_id = move.account_dest_id

                # credit_account_id = self.env['account.account']
                # debit_account_id = self.env['account.account']
                
                # journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()

                # is_returned = False
                # if move._is_in():
                #     if move._is_returned(valued_type='in'):
                #         is_returned = True
                #         credit_account_id = account_id
                #         debit_account_id = account_dest_id
                #     else:
                #         credit_account_id = account_dest_id
                #         debit_account_id = account_id
                # elif move._is_out():
                #     if move._is_returned(valued_type='out'):
                #         is_returned = True
                #         credit_account_id = account_dest_id
                #         debit_account_id = account_id
                #     else:
                #         credit_account_id = account_id
                #         debit_account_id = account_dest_id

                if account_move_id:
                    to_write = []
                    need_run = len(account_move_id.line_ids.mapped('account_id')) == 2
                    if not need_run:
                        continue

                    for aml in account_move_id.line_ids:
                        new_debit = 0.0
                        new_credit = 0.0
                        new_amount_currency = 0.0
                        is_debit = aml.balance > 0
                        if is_debit:
                            new_debit = value
                            new_amount_currency = new_price_unit * svl.quantity if aml.currency_id.name == 'VND' else self.price_unit * svl.quantity * rate
                        else:
                            new_credit = value
                            new_amount_currency = new_price_unit * svl.quantity * -1 if aml.currency_id.name == 'VND' else self.price_unit * svl.quantity * -1 * rate
                        to_write.append((1, aml.id, { 'debit': new_debit, 'credit': new_credit, 'amount_currency': new_amount_currency,}))
                    if to_write:
                        account_move_id.sudo().write({'line_ids': to_write})

                # elif credit_account_id and debit_account_id:
                #     if move._is_out():
                #         value *= -1
                #     account_moves = self.env['account.move'].sudo().with_user(1).create(move.with_company(1).with_context(is_returned=is_returned, force_period_date=move.date)._prepare_account_move_vals(credit_account_id.id, debit_account_id.id,journal_id, svl.quantity, svl.description, svl.id, value))
                #     account_moves.action_post()

