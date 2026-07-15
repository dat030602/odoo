from odoo import models, fields, api
import logging
from datetime import datetime, date
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError
from .component import vietnam_number
import pytz

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    contact_total_due = fields.Monetary(string="Tổng công nợ", currency_field='currency_id', compute="_compute_contact_total_due",related=False)


    credit_limit = fields.Monetary(string='Hạn mức công nợ', compute="_compute_credit_debit_limit")
    contract_number = fields.Char(string='Số hợp đồng', related='partner_id.contract_number')

    delay_days = fields.Integer(string='Thời gian chậm thanh toán', related='partner_id.delay_days')
    penalty_debt = fields.Monetary(string='Lãi phạt', compute="_compute_credit_debit_limit")
    total_debt = fields.Monetary(string='Tổng tiền Nợ', related='partner_id.total_debt')
    date_due = fields.Char(string='Hạn thanh toán', compute="_compute_date_due")
    credit_due = fields.Monetary(string='Lãi quá hạn', compute="_compute_credit_due")

    is_delivered = fields.Boolean(string="Đã giao",default=False,copy=False)
    
    payment_type = fields.Selection(string='Hình thức thanh toán',selection=[
        ('bank','Thanh toán chuyển khoản'),
        ('cash','Thanh toán tiền mặt'),
    ],default='bank')

    @api.model
    def default_get(self, fields_list):
        defaults = super(SaleOrder, self).default_get(fields_list)
        defaults.update({
            'origin': 'Zalo',
        })
        return defaults
    
    
    @api.depends('partner_id.credit')
    def _compute_contact_total_due(self):
        for rec in self:
            credit = 0
            if rec.partner_id:
                credit = rec.partner_id.credit
            rec.contact_total_due = credit

    @api.depends('picking_ids', 'picking_ids.state','is_delivered','picking_ids.move_ids.quantity_done')
    def _compute_delivery_status(self):
        super(SaleOrder,self)._compute_delivery_status()
        for order in self:
            current_delivery_status = order.delivery_status 
            total_delivered = sum(line.qty_delivered for line in order.order_line.filtered(lambda l: 'tấn' in l.product_uom.name.lower()))
            total_ordered = sum(line.product_uom_qty for line in order.order_line.filtered(lambda l: 'tấn' in l.product_uom.name.lower()))
            if order.is_delivered:
                current_delivery_status = 'full'
            elif current_delivery_status == 'full' and total_delivered < total_ordered:
                current_delivery_status = 'partial'
            elif total_delivered >= total_ordered and total_ordered > 0:
                current_delivery_status = 'full'
            order.delivery_status = current_delivery_status
    
    def action_confirm_delivered(self):
        for order in self:
            order.is_delivered = True

    @api.depends('partner_id.use_partner_credit_limit','partner_id.credit_limit')
    def _compute_credit_debit_limit(self):
        for rec in self:
            rec.credit_limit = rec.partner_id.credit_limit if rec.partner_id.use_partner_credit_limit else 0
            rec.penalty_debt = rec.partner_id.late_interest + rec.partner_id.penalty_debt
        
    @api.depends('partner_id')
    def _compute_credit_due(self):
        for rec in self:
            invs = self.env['account.move'].sudo().search([
                ('partner_id', '=', rec.id),
                ('invoice_date_due', '>', datetime.now().strftime('%Y-%m-%d')),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial'))
            ])
            rec.credit_due = sum(invs.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable').mapped('amount_residual')) if invs else 0

    def get_report_saleorder_2025_docx_context(self):
        tz = pytz.timezone(self.env.user.tz)
        cur_date = datetime.now(tz)
        str_date = cur_date.strftime('%Hh%M ngày %d/%m/%Y')

        total_purchase_debt = self.contact_total_due
        overdue_purchase_debt = self.credit_due
        overdue_interest = self.penalty_debt
        total_debt_plus_interest = self.total_debt

        new_order_qty = sum(self.order_line.filtered(lambda l: 'tấn' in l.product_uom.name.lower()).mapped('product_uom_qty'))
        new_order_amount = self.amount_total

        old_orders = self.env['sale.order'].search([('partner_id','=',self.partner_id.id),('delivery_status','!=','full'),('state','!=','cancel')]) - self
        old_undelivered_orders = []

        for order in old_orders:
            lines = order.order_line.filtered(lambda l:l.product_uom_qty > l.qty_delivered and 'tấn' in l.product_uom.name.lower())
            product_uom_qty = lines.mapped('product_uom_qty')
            qty_delivered = lines.mapped('qty_delivered')
            amount = 0
            for line in lines:
                taxes = line.tax_id.compute_all(line.price_unit, line.order_id.currency_id, line.product_uom_qty - line.qty_delivered, product=line.product_id, partner=line.order_id.partner_id)
                amount += taxes['total_included']
            old_undelivered_orders.append({'name': order.name, 'quantity': sum(product_uom_qty) - sum(qty_delivered), 'amount': amount})
        
        formatted_old_orders = ''
        for order in old_undelivered_orders:
            formatted_quantity = f"{order['quantity']:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
            formatted_old_orders += f"\n+ {order['name']}: {formatted_quantity} tấn - {int(order['amount']):,} đồng"

        return {
            'company': self.env.company,
            'saleorder': self,
            'date_order': self.date_order and self.date_order.strftime('%d/%m/%Y') or '',
            'commitment_date': self.get_commitment_date_timezone(),
            'phone': self.get_phone(),
            'amount_in_words': (vietnam_number(int(self.amount_total)) + ' đồng chẵn').title(),
            'note': self.get_note(),
            'internal_note': self.get_internal_note(),
            'sum_product_uom_qty': self.get_sum_product_uom_qty(),
            'sum_product_uom_qty_tan': self.get_sum_product_uom_qty_tan(),
            'sum_product_uom_qty_khac': self.get_sum_product_uom_qty_khac(),
            'note_sale': self.get_note_sale(),
            'noted_sale': self.get_noted_sale(),
            'address': self.get_address(),
            'date': str_date,
            'payment_type': dict(self._fields['payment_type'].selection).get(self.payment_type),

            'tong_cong_no_mua_hang': f"{int(total_purchase_debt):,}" + f" đồng lúc {str_date}",
            'cong_no_qua_han_mua_hang': f"{int(overdue_purchase_debt):,}" + f" đồng lúc {str_date}",
            'lai_suat_qua_han': f"{int(overdue_interest):,}" + f" đồng lúc {str_date}",
            'tong_cong_no_mua_hang_lai_suat': f"{int(total_debt_plus_interest):,}" + f" đồng lúc {str_date}",
            'so_tien_don_hang_moi_se_nhan': f"{new_order_qty:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".") + f" tấn - {int(new_order_amount):,}" + " đồng",
            'so_tien_don_hang_cu_chua_nhan': formatted_old_orders,
            'partner_bank_name': self.partner_id.bank_ids[0].bank_id.name if self.partner_id.bank_ids and self.partner_id.bank_ids[0].bank_id else '',
            'partner_bank_acc': self.partner_id.bank_ids[0].acc_number if self.partner_id.bank_ids else '',
            'team_id': self.team_id.name or '',
            'representative_phone': self.partner_id.representative_phone or '',
            'sales_user': (self.user_id.name + (' - ' + self.user_id.phone if self.user_id.phone else '')) if self.user_id else '',
            'fax': self.partner_id.fax or '',
        }
    
    def get_report_saleorder_docx_context(self):
        res = super(SaleOrder,self).get_report_saleorder_docx_context()
        res.update({
            'payment_type': dict(self._fields['payment_type'].selection).get(self.payment_type),
        })
        return res

    