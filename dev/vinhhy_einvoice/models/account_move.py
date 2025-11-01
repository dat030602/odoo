# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    partner_vat_id = fields.Many2one('partner.vat', 'Legal VH E-Invoice Company', tracking=True, domain="[('company_type','=','company')]")
    partner_contact_id = fields.Many2one('partner.vat', 'VH E-Invoice Contact', tracking=True)
    vh_einv_ids = fields.Many2many('vinhhy.einvoice', 'vh_einv_account_move_rel', 'move_id','vh_einv_id', string='Vinh Hy E-Invoice', copy=False)
    vh_einv_ref = fields.Char('VH E-Invoice Reference', compute='_compute_vh_einv_ref', store=True, tracking=True)
    vh_einv_count = fields.Integer('VH E-Invoices Count', compute='_compute_vh_einv_ref')

    def _search_sudo_vh_einv(self):
        lst_ei_id = []
        if not isinstance(self.id, models.NewId):
            query = """
                SELECT move.vh_einv_id FROM vh_einv_account_move_rel move
                WHERE move_id = %(move_id)s;
                """
            self.env.cr.execute(query, {'move_id': self.id})
            res = self.env.cr.dictfetchall()
            for dict in res:
                if dict['vh_einv_id'] not in lst_ei_id:
                    lst_ei_id.append(dict['vh_einv_id'])
        return lst_ei_id

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
            'invoice_ids': [(4, self.id)],
            'partner_id': self.partner_contact_id and self.partner_contact_id.id or False,
            'partner_vat_id': self.partner_vat_id and self.partner_vat_id.id or False,
            'date_invoice': self.invoice_date,
            'company_id': self.company_id.id,
            'journal_id': self.journal_id.id,
            'company_currency_id': self.company_currency_id.id,
            'currency_id': self.currency_id.id,
            'fiscal_position_id': self.fiscal_position_id and self.fiscal_position_id.id,
            # VH E-Invoice Data Information
            'user_id': self.invoice_user_id.id if self.invoice_user_id else False,
            'team_id': self.team_id.id if self.team_id else False,
            'customer_email': self.partner_vat_id and self.partner_vat_id.email or False,
        }
        einv_line_vals = self._prepare_einv_line_values()
        vinhhy_einv_val['line_ids'] = einv_line_vals
        vinhhy_einv_obj = self.env['vinhhy.einvoice'].create(vinhhy_einv_val)
        return vinhhy_einv_obj

    def _prepare_einv_line_values(self):
        line_vals = []
        for line in self.invoice_line_ids:
            name = line.product_id.name or ''
            vat_product = line.product_id._get_vat_product_template()
            vat_product_tax = vat_product.taxes_ids[0].id if vat_product.taxes_ids else False
            invoice_tax_id = line.tax_ids[0] if line.tax_ids else False
            if invoice_tax_id:
                tax = self.env['einvoice.tax'].search([]).filtered(lambda x: x.amount == invoice_tax_id.amount)
            else:
                tax = False
            val = (0, 0, {
                'name': name,
                # 'origin': name,
                'account_id': line.account_id.id,
                'price_unit': vat_product.price if vat_product else line.price_unit,
                'quantity': line.quantity,
                'discount': line.discount,
                'uom_id': line.product_id.uom_id.id,
                'product_id': line.product_id.id or False,
                'vat_product_id': vat_product.id if vat_product else False,
                'vh_inv_line_tax_id': tax and tax.id or vat_product_tax,
                'inv_line_source_id': line.id
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
