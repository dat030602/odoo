# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _default_creator_id(self):
        return self.env.user

    def _default_chief_accountant_id(self):
        chief_accountant_id = self.env['ir.config_parameter'].sudo().get_param('ccv_sql.chief_accountant_id', False)
        if chief_accountant_id:
            return self.env['res.users'].sudo().browse(int(chief_accountant_id))
        return False

    def _default_unit_head_id(self):
        unit_head_id = self.env['ir.config_parameter'].sudo().get_param('ccv_sql.unit_head_id', False)
        if unit_head_id:
            return self.env['res.users'].sudo().browse(int(unit_head_id))
        return False

    sale_id = fields.Many2one('sale.order','Order',copy=False)
    purchase_id = fields.Many2one('purchase.order','Purchase',copy=False)
    creator_id = fields.Many2one('res.users',default=_default_creator_id)
    chief_accountant_id = fields.Many2one('res.users',default=_default_chief_accountant_id)
    unit_head_id = fields.Many2one('res.users',default=_default_unit_head_id)

    def copy(self, default=None):
        default = default or {}
        if self.partner_id:
            default['partner_id'] = self.partner_id.id
        if self.date:
            default['date'] = self.date
        if self.journal_id and not default.get("journal_id"):
            default['journal_id'] = self.journal_id.id
        if self.unit_head_id:
            default['unit_head_id'] = self.unit_head_id.id
        if self.creator_id:
            default['creator_id'] = self.creator_id.id
        if self.chief_accountant_id:
            default['chief_accountant_id'] = self.chief_accountant_id.id
        if self.number_ctnb:
            default['number_ctnb'] = self.number_ctnb
        # if self.payment_method_line_id:
            # default['payment_method_line_id'] = self.payment_method_line_id.id
        return super(AccountPayment, self).copy(default)
       
    @api.onchange('sale_id','purchase_id')
    def onchange_sale_id(self):
        for res in self:
            if res.sale_id:
                res.partner_id = res.sale_id.partner_id
                res.amount = res.sale_id.amount_total
            if res.purchase_id:
                res.partner_id = res.purchase_id.partner_id
                res.amount = res.purchase_id.amount_total

    @api.onchange('payment_type')
    def onchange_payment_type(self):
        for res in self:
            if res.payment_type == 'inbound':
                res.ref = 'Thu tiền bán hàng từ - TT đơn hàng'
            if res.payment_type == 'outbound':
                res.ref = 'Công ty CCV'

    def action_post(self):
        post = super(AccountPayment,self).action_post()
        self.update_move()
        return post

    def update_move(self):
        if self.move_id:
            self.move_id.partner_id = self.partner_id
            self.move_id.partner_vat_id = self.partner_id
            self.move_id.note = self.note
            if self.move_id.ref or self.move_id.note:
                text = self.move_id.note if self.move_id.note else self.move_id.ref
                for line in self.move_id.line_ids:
                    line.name = text

    @api.model
    def create(self,vals):
        res = super(AccountPayment,self).create(vals)
        res.update_move()
        return res

    def write(self,vals):
        res = super(AccountPayment,self).write(vals)
        for rec in self:
            rec.update_move()
        return res