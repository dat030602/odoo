from odoo import models, fields, api

def _convert_amount_to_company_currency(account_move_id, amount):
    """Convert amount to company currency based on manual or automatic exchange rate"""
    if account_move_id.apply_manual_currency_exchange:
        if account_move_id.inverse_manural_currency_exchange_rate > 0:
            return amount * account_move_id.inverse_manural_currency_exchange_rate
        return amount / account_move_id.manual_currency_exchange_rate
    return account_move_id.currency_id._convert(amount, account_move_id.company_id.currency_id, account_move_id.company_id, account_move_id.date)

class WzAccountMoveImportTaxLine(models.TransientModel):
    _name = 'wz.account.move.import.tax.line'
    _description = 'Dòng đơn hàng trong wizard'

    wizard_id = fields.Many2one('wz.account.move.import.tax', string="Wizard")
    move_id = fields.Many2one('account.move', string="Hóa đơn")
    account_id = fields.Many2one('account.account', string="Tài khoản")
    product_id = fields.Many2one('product.product', string="Sản phẩm")
    tax_id = fields.Many2one('account.tax', string="Thuế", domain="[('type_tax_use','=','purchase')]")
    price_total = fields.Monetary(string="Tổng")
    price_tax = fields.Monetary(string="Giá thuế", currency_field='currency_id')
    price_tax_w_company_currency = fields.Monetary(string="Giá thuế (tiền tệ công ty)", currency_field='currency_company_id')
    currency_id = fields.Many2one('res.currency', string="Tiền tệ")
    currency_company_id = fields.Many2one('res.currency', string="Tiền tệ công ty")

    @api.onchange('product_id','tax_id','price_total')
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id and rec.tax_id and rec.price_total:
                taxes = rec.tax_id.compute_all(rec.price_total, currency=rec.currency_id)
                rec.price_tax = taxes['total_included'] - taxes['total_excluded']
                rec.price_tax_w_company_currency = _convert_amount_to_company_currency(rec.move_id, rec.price_tax)
            else:
                rec.price_tax = 0
                rec.price_tax_w_company_currency = 0

class WzAccountMoveImportTax(models.TransientModel):
    _name = 'wz.account.move.import.tax'
    _description = 'Wizard thuế nhập khẩu cho hóa đơn'

    account_move_id = fields.Many2one('account.move', string="Hóa đơn")
    line_ids = fields.One2many('wz.account.move.import.tax.line', 'wizard_id', string="Thuế nhập khẩu")

    @api.onchange('account_move_id')
    def _onchange_account_move_id(self):
        for rec in self:
            rec.line_ids = [(5, 0, 0)]
            line_ids = []
            for line in rec.account_move_id.invoice_line_ids:
                line_ids.append((0, 0, {
                    'product_id': line.product_id.id,
                    'account_id': line.account_id.id,
                    'move_id': rec.account_move_id.id,
                    'price_total': line.price_total,
                    'currency_id': rec.account_move_id.currency_id.id,
                    'currency_company_id': rec.account_move_id.company_id.currency_id.id,
                }))
            rec.line_ids = line_ids

    def _prepare_values(self):
        lines = []
        line_ids = self.line_ids.filtered(lambda x: x.price_tax > 0)
        price_tax = sum(self.line_ids.mapped('price_tax'))
        tax_ids = self.line_ids.mapped('tax_id')
        account_ids = self.line_ids.mapped('account_id')

        groups = {}

        for tax_id in tax_ids:
            account_tax_id = tax_id.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').mapped('account_id')
            for account_id in account_ids:
                merge = (account_tax_id.id, account_id.id)
                line = line_ids.filtered(lambda x: x.account_id == account_id and x.tax_id == tax_id)
                if not line:
                    continue
                price_tax = sum(line.mapped('price_tax'))
                price_tax_w_company_currency = sum(line.mapped('price_tax_w_company_currency'))
                groups.setdefault(merge, {
                    'amount_currency': price_tax,
                    'balance': price_tax_w_company_currency,
                })
        for key, value in groups.items():
            balance = value.get('balance')
            amount_currency = value.get('amount_currency')
            lines.append((0, 0, {
                'account_id': key[0],
                'amount_currency': -amount_currency,
                'balance': -balance,
                'currency_id': self.account_move_id.currency_id.id,
            }))
            lines.append((0, 0, {
                'account_id': key[1],
                'amount_currency': amount_currency,
                'balance': balance,
                'currency_id': self.account_move_id.currency_id.id,
            }))
        return {
            'ref': self.account_move_id.ref or '',
            'move_type': 'entry',
            'narration': self.account_move_id.narration,
            'currency_id': self.account_move_id.currency_id.id,
            'partner_id': self.account_move_id.partner_id.id,
            'fiscal_position_id': self.account_move_id.fiscal_position_id.id,
            'payment_reference': self.account_move_id.payment_reference,
            'partner_bank_id': self.account_move_id.partner_bank_id.id,
            'invoice_origin': self.account_move_id.invoice_origin,
            'invoice_payment_term_id': self.account_move_id.invoice_payment_term_id.id,
            'line_ids': lines,
            'company_id': self.account_move_id.company_id.id,
            'user_id': self.account_move_id.user_id.id,
            'apply_manual_currency_exchange': self.account_move_id.apply_manual_currency_exchange,
            'inverse_manural_currency_exchange_rate': self.account_move_id.inverse_manural_currency_exchange_rate,
            'manual_currency_exchange_rate': self.account_move_id.manual_currency_exchange_rate,
            'date': self.account_move_id.date,
            'invoice_date': self.account_move_id.invoice_date,
            'report_date': self.account_move_id.report_date,
        }

    def action_create_invoice(self):
        invoice = self.env['account.move'].create(self._prepare_values())
        invoice.action_post()
        self.account_move_id.write({'move_tax_import_id': invoice.id})
        self.account_move_id.invoice_line_ids.purchase_order_id._compute_invoice()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
