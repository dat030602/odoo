# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    gift_entries = fields.Boolean('Gift entries',copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('stock_move_id'):
                sm = self.env['stock.move'].browse(vals['stock_move_id'])
                # User requested to disable automatic creation of gift entries based on '6418' picking type
                # if sm.picking_id and sm.picking_id.picking_type_id and '6418' in (sm.picking_id.picking_type_id.name or ''):
                #     if sm.sale_line_id and sm.sale_line_id.price_unit == 0 and sm.sale_line_id.tax_id:
                #         vals['gift_entries'] = True
                #         if 'is_gift_entries' in self.env['account.move']._fields:
                #             vals['is_gift_entries'] = True
                        
        res = super(AccountMove, self).create(vals_list)
        for rec in res:
            if rec.gift_entries:
                rec.edit_credit_gift_entries()
        return res

    @api.onchange('is_gift_entries')
    def onchange_is_gift_entries(self):
        for rec in self:
            rec.gift_entries = rec.is_gift_entries

    @api.onchange('gift_entries')
    def onchange_gift_entries(self):
        for res in self:
            if res.gift_entries:
                # We only validate if the move can be processed (needs draft state and move lines)
                if not res.state == 'draft':
                    raise ValidationError(_('Cannot compute gift tax on a posted entry.'))

    def edit_credit_gift_entries(self):
        for rec in self:
            if rec.state == 'draft':
                # 1. Find correct expense account
                expense_line = rec.line_ids.filtered(lambda x: x.debit > 0 and not x.tax_line_id and x.display_type not in ('line_section', 'line_note'))
                if not expense_line:
                    continue
                correct_expense_account = expense_line[0].account_id

                # 2. Get tax info and base amount
                tax_rec = False
                if rec.stock_move_id and rec.stock_move_id.sale_line_id and rec.stock_move_id.sale_line_id.tax_id:
                    tax_rec = rec.stock_move_id.sale_line_id.tax_id[0]
                else:
                    # Fallback to 8% tax (ID 35) or search by name/amount
                    tax_rec = rec.env['account.tax'].browse(35)
                    if not tax_rec.exists():
                        tax_rec = rec.env['account.tax'].search([('type_tax_use', '=', 'sale'), ('amount', '=', 8.0)], limit=1)

                if not tax_rec:
                    raise ValidationError(_('Cannot find 8% sales tax record to compute gift tax.'))

                inventory_line = rec.line_ids.filtered(lambda x: x.credit > 0 and not x.tax_line_id and x.display_type not in ('line_section', 'line_note'))
                if not inventory_line:
                    continue

                base_amount = inventory_line[0].credit
                tax_amount = round(base_amount * (tax_rec.amount / 100.0))

                # 3. Get tax account
                tax_account = tax_rec.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax').account_id
                if not tax_account:
                    tax_account = rec.env['account.account'].search([('code', '=', '33311')], limit=1)

                # Unlink old tax lines or balancing lines if any
                rec.line_ids.filtered(lambda x: x.tax_line_id or x.display_type == 'tax' or x.name == _('Automatic Balancing Line')).unlink()

                # 4. Create new line values
                new_lines_vals = [
                    {
                        'name': f"Thuế GTGT đầu ra hàng biếu tặng - {inventory_line[0].name}",
                        'move_id': rec.id,
                        'account_id': correct_expense_account.id,
                        'debit': tax_amount,
                        'credit': 0.0,
                    },
                    {
                        'name': f"Thuế GTGT phải nộp {tax_rec.amount}% - {inventory_line[0].name}",
                        'move_id': rec.id,
                        'account_id': tax_account.id,
                        'debit': 0.0,
                        'credit': tax_amount,
                        'tax_line_id': tax_rec.id,
                    }
                ]
                rec.env['account.move.line'].with_context(check_move_validity=False).create(new_lines_vals)
            else:
                raise ValidationError(_('Cannot compute gift tax on a posted entry.'))

    def write(self, vals):
        if 'is_gift_entries' in vals:
            vals['gift_entries'] = vals['is_gift_entries']
        res = super(AccountMove, self).write(vals)
        if 'gift_entries' in vals or 'is_gift_entries' in vals:
            for rec in self:
                if rec.gift_entries or rec.is_gift_entries:
                    rec.edit_credit_gift_entries()
        return res

    def create_data_sinvoice(self):
        self.ensure_one()
        
        # Tự động sinh bút toán thuế (nếu đủ điều kiện 6418) NGAY LÚC bấm phát hành hóa đơn
        if not self.gift_entries and self.stock_move_id and self.stock_move_id.picking_id.picking_type_id and '6418' in (self.stock_move_id.picking_id.picking_type_id.name or ''):
            if self.stock_move_id.sale_line_id and self.stock_move_id.sale_line_id.price_unit == 0 and self.stock_move_id.sale_line_id.tax_id:
                was_posted = (self.state == 'posted')
                if was_posted:
                    self.button_draft() # Phải chuyển về nháp mới tính toán lại được dòng thuế
                
                # Gọi write sẽ tự động trigger hàm edit_credit_gift_entries
                self.write({'gift_entries': True, 'is_gift_entries': True})
                
                if was_posted:
                    self.action_post() # Vào sổ lại

        if not self.gift_entries:
            return super(AccountMove,self).create_data_sinvoice()
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
            'partner_vat_name': partner_vat.name_vat
        }
        sinvoice_id = self.env['viettel.sinvoice'].create(val_sinvoice)
        if sinvoice_id:
            data_obj = self.env['viettel.sinvoice.data']
            for line in self.line_ids.filtered(lambda x: x.debit > 0 and x.product_id):
                vals = sinvoice_id.create_data_sinvoice_line_gift_entries(line)
                for val in vals:
                    data_obj.create(val)
        return True 
