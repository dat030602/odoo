from odoo import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        return []

    def _post(self, soft=True):
        for invoice_id in self.sudo().filtered(lambda m: m.move_type == 'entry' and not m.tax_cash_basis_origin_move_id and m.stock_valuation_layer_ids):
            if invoice_id.line_ids.tax_ids:
                continue
            line_ids = invoice_id.line_ids.filtered(lambda l:l.display_type == 'product' and l.product_id.is_gift_product and l.account_id.account_type == 'asset_current')
            for line in line_ids:
                line.tax_ids = [(6, 0, line.product_id.taxes_id.ids)]
        for invoice_id in self.sudo().filtered(lambda m: m.state != 'posted' and m.move_type == 'entry' and not m.tax_cash_basis_origin_move_id and m.stock_valuation_layer_ids):
            line_ids = invoice_id.line_ids
            product_id = line_ids.filtered(lambda l:l.display_type == 'product').product_id
            product_id = product_id[0] if product_id else False
            to_write = invoice_id.line_ids.filtered(lambda l:l.account_id == invoice_id.company_id.account_journal_suspense_account_id)
            # Viết lại bằng SQL
            if product_id and product_id.categ_id and product_id.categ_id.property_stock_valuation_account_id:
                account_id = product_id.categ_id.property_stock_account_output_categ_id.id
                prod_id = product_id.id
                line_ids_to_update = to_write.ids
                if line_ids_to_update:
                    query = """
                        UPDATE account_move_line
                        SET account_id = %s,
                            product_id = %s
                        WHERE id = ANY(%s)
                    """
                    self.env.cr.execute(query, (account_id, prod_id, line_ids_to_update))
        res = super(AccountMove,self)._post(soft)
        return res

