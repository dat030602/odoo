# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_vat_id = fields.Many2one('partner.vat', 'Legal VH E-Invoice Company', tracking=True, domain="[('company_type','=','company')]")
    partner_contact_id = fields.Many2one('partner.vat', 'VH E-Invoice Contact', tracking=True)
    vh_einv_ids = fields.Many2many('vinhhy.einvoice', 'vh_einv_sale_order_rel', 'sale_id','vh_einv_id', string='Vinh Hy E-Invoice', copy=False)
    vh_einv_ref = fields.Char('VH E-Invoice Reference', compute='_compute_vh_einv_ref', store=True, tracking=True)
    vh_einv_count = fields.Integer('VH E-Invoices Count', compute='_compute_vh_einv_ref')

    @api.depends('vh_einv_ids', 'vh_einv_ids.state', 'vh_einv_ids.name')
    def _compute_vh_einv_ref(self):
        for move in self:
            issued_ei = move.vh_einv_ids.filtered(lambda einv: einv.state == 'CM')
            move.vh_einv_ref = ' - '.join(sorted(issued_ei.mapped('name')))
            move.vh_einv_count = len(issued_ei.ids)

    def action_create_einvoice(self):
        if not self.partner_vat_id and not self.partner_contact_id:
            raise UserError(_("You must have partner to invoice!"))
        vinhhy_einv_val = {
            'sale_ids': [(4, self.id)],
            'partner_id': self.partner_contact_id and self.partner_contact_id.id or False,
            'partner_vat_id': self.partner_vat_id and self.partner_vat_id.id or False,
            'date_invoice': self.date_order,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'fiscal_position_id': self.partner_vat_id.partner_id.property_account_position_id.id \
                if self.partner_vat_id and self.partner_vat_id.partner_id else self.partner_contact_id.partner_id.property_account_position_id.id \
                    if self.partner_contact_id and self.partner_contact_id.partner_id else False, #FIXME
            # VH E-Invoice Data Information
            'user_id': self.user_id.id if self.user_id else False,
            'team_id': self.team_id.id if self.team_id else False,
            'customer_email': self.partner_vat_id and self.partner_vat_id.email or False,
        }
        einv_line_vals = self._prepare_einv_line_values()
        vinhhy_einv_val['line_ids'] = einv_line_vals
        vinhhy_einv_obj = self.env['vinhhy.einvoice'].create(vinhhy_einv_val)
        return vinhhy_einv_obj

    def _prepare_einv_line_values(self):
        line_vals = []
        for line in self.order_line:
            name = line.product_id.name or ''
            vat_product = line.product_id._get_vat_product_template()
            vat_product_tax = vat_product.taxes_ids[0].id if vat_product.taxes_ids else False
            # Recompute tax for VAT Invoice
            invoice_tax_id = line.tax_id[0] if line.tax_id else False
            if invoice_tax_id:
                tax = self.env['einvoice.tax'].search([]).filtered(lambda x: x.amount == invoice_tax_id.amount)
            else:
                tax = False
            val = (0, 0, {
                'name': name,
                'price_unit': vat_product.price if vat_product else line.price_unit,
                'quantity': line.product_uom_qty,
                'discount': line.discount,
                'uom_id': vat_product.uom_id.id if vat_product else line.product_uom.id,
                'product_id': line.product_id.id or False,
                'vat_product_id': vat_product.id if vat_product else False,
                'vh_inv_line_tax_id': tax and tax.id or vat_product_tax,
                'sale_line_source_id': line.id #FIXME
            })
            line_vals.append(val)
        return line_vals

    def action_create_view_vh_einv(self):
        vinhhy_einv_obj = self.action_create_einvoice()
        view = self.env.ref('vinhhy_einvoice_service.vinhhy_einvoice_form')
        return {
            'name': _('Vinh Hy E-Invoice'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'vinhhy.einvoice',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': vinhhy_einv_obj.id,
            'context': dict(self.env.context, create=False)
        }
    
    def action_create_vh_inv_with_multi_so(self):
        partner_contact_id = self.mapped('partner_contact_id')
        partner_vat_id = self.mapped('partner_vat_id')
        currency_id = self.mapped('currency_id')
        if len(partner_vat_id) > 1 or len(partner_contact_id) > 1:
            raise UserError(_("It is not possible to merge orders for many different customers."))
        if len(currency_id) > 1:
            raise UserError(_("It is not possible to merge orders for different currencies."))
        if not partner_contact_id and not partner_vat_id:
            raise UserError(_("Can not find the customer to invoice!"))
        if any(so.state not in ['sale', 'done'] for so in self):
            raise UserError(_('Orders must be confirmed or done.'))
        first_so_in_lst = self[0]
        vinhhy_einv_val = {
            # 'sale_ids': [(4, self.id)],
            'partner_id': first_so_in_lst.partner_contact_id and first_so_in_lst.partner_contact_id.id or False,
            'partner_vat_id': first_so_in_lst.partner_vat_id and first_so_in_lst.partner_vat_id.id or False,
            'date_invoice': first_so_in_lst.date_order,
            'company_id': first_so_in_lst.company_id.id,
            'currency_id': first_so_in_lst.currency_id.id,
            'fiscal_position_id': first_so_in_lst.partner_vat_id.partner_id.property_account_position_id.id \
                if first_so_in_lst.partner_vat_id and first_so_in_lst.partner_vat_id.partner_id else first_so_in_lst.partner_contact_id.partner_id.property_account_position_id.id \
                    if first_so_in_lst.partner_contact_id and first_so_in_lst.partner_contact_id.partner_id else False, #FIXME
            # VH E-Invoice Data Information
            'user_id': first_so_in_lst.user_id.id if first_so_in_lst.user_id else False,
            'team_id': first_so_in_lst.team_id.id if first_so_in_lst.team_id else False,
            'customer_email': first_so_in_lst.partner_vat_id and first_so_in_lst.partner_vat_id.email or False,
        }
        sale_ids = []
        for so in self:
            sale_ids.append((4, so.id))
            for line in so.order_line:
                existing_ei_line = -1
                tax_ids = line.tax_id.ids[0] if line.tax_id else False
                # tìm thuế hđđt
                tax = self.env['einvoice.tax'].sudo()
                if tax_ids:
                    tax = tax.search([('amount','=',line.tax_id[0].amount)], limit=1)
                # tìm sản phẩm thuế và thuế trên sản phẩm thuế
                vat_product = line.product_id._get_vat_product_template()
                vat_product_tax = vat_product.taxes_ids[0].id if vat_product.taxes_ids else False
                tax_to_use = tax.id if tax else vat_product_tax
                # đã tồn tại line data
                if "line_ids" in vinhhy_einv_val:
                    for l_indx, vh_inv_line in enumerate(vinhhy_einv_val['line_ids']):
                        line_val = vh_inv_line[-1]  # data easy invoice line
                        # Trường hợp cùng sản phẩm cùng đơn giá
                        if line_val['product_id'] == line.product_id.id and line_val['price_unit'] == line.price_unit:
                            # kiểm tra cùng đơn vị cùng chính sách thuế
                            if line_val['vh_inv_line_tax_id'] != tax_to_use or line_val['uom_id'] != line.product_id.uom_id.id:
                                raise UserError(_('The same product must have the same unit and tax policy!'))
                            else:
                                existing_ei_line = l_indx
                                break
                        # trường hợp cùng sản phẩm khác đơn giá
                        if line_val['product_id'] == line.product_id.id and line_val['price_unit'] != line.price_unit:
                            # kiểm tra cùng đơn vị cùng chính sách thuế
                            if line_val['vh_inv_line_tax_id'] != tax_to_use or line_val['uom_id'] != line.product_id.uom_id.id:
                                raise UserError(_('The same product must have the same unit and tax policy!'))
                            else:
                                # cần tạo line mới
                                break
                    if existing_ei_line >= 0:  # cập nhật lại số lượng vào easy invoice line đã tồn tại
                        vinhhy_einv_val['line_ids'][existing_ei_line][-1]['quantity'] += line.product_uom_qty
                    else:
                        product_name = line.product_id.name or ''
                        # thêm 1 line mới vào vinh hy invoice line data
                        vinhhy_einv_val['line_ids'].append((0, 0, {
                            'name': line.product_id.name or '',
                            'price_unit': vat_product.price if vat_product else line.price_unit,
                            'quantity': line.product_uom_qty,
                            'discount': line.discount,
                            'uom_id': vat_product.uom_id.id if vat_product else line.product_uom.id,
                            'product_id': line.product_id.id or False,
                            'vat_product_id': vat_product.id if vat_product else False,
                            'vh_inv_line_tax_id': tax_to_use,
                            'sale_line_source_id': line.id #FIXME
                        }))
                else:  # chưa tồn tại easy invoice line data
                    line_vals = []
                    if line.display_type or not line.product_id:
                        continue
                    product_name = line.product_id.name or ''
                    line_vals.append((0, 0, {
                            'name': line.product_id.name or '',
                            'price_unit': vat_product.price if vat_product else line.price_unit,
                            'quantity': line.product_uom_qty,
                            'discount': line.discount,
                            'uom_id': vat_product.uom_id.id if vat_product else line.product_uom.id,
                            'product_id': line.product_id.id or False,
                            'vat_product_id': vat_product.id if vat_product else False,
                            'vh_inv_line_tax_id': tax_to_use,
                            'sale_line_source_id': line.id #FIXME
                        }))
                    vinhhy_einv_val['line_ids'] = line_vals
        if sale_ids:
            vinhhy_einv_val.update({'sale_ids': sale_ids})
        vinhhy_einv_obj = self.env['vinhhy.einvoice'].create(vinhhy_einv_val)
        view = self.env.ref('vinhhy_einvoice_service.vinhhy_einvoice_form')
        return {
            'name': _('Vinh Hy E-Invoice'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'vinhhy.einvoice',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': vinhhy_einv_obj.id,
            'context': dict(self.env.context, create=False)
        }
