from odoo import models, fields, api
import logging
import pytz
from datetime import datetime
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError
from .component import vietnam_number

_logger = logging.getLogger(__name__)

class purchase_order(models.Model):
    _inherit = "purchase.order"

    read_amount_subtotal = fields.Char(compute="_compute_read_amount")
    read_amount_untax = fields.Char(compute="_compute_read_amount")
    transportation_id = fields.Many2one('ccv.data.src',string="Phương thức vận chuyển", domain=[('type','=','single')])
    requirement_id = fields.Many2one('ccv.data.src',string="Yêu cầu thêm", domain=[('type','=','multi')])
    
    @api.onchange('requirement_id','order_line')
    def _onchange_requirement_id(self):
        for rec in self:
            factory = self.env['factory.product.default'].sudo()
            for line in rec.order_line:
                factory = factory.search([('product_ids','in',[line.product_id._origin.id])],limit=1)
                if factory:
                    rec.picking_type_id = factory.picking_type_id.warehouse_id.in_type_id
                    break
            if not factory and rec.requirement_id.picking_type_id:
                rec.picking_type_id = rec.requirement_id.picking_type_id.id

    @api.depends('amount_untaxed','amount_total')
    def _compute_read_amount(self):
        for rec in self:
            rec.read_amount_subtotal = self.convert_money(rec.amount_total)
            rec.read_amount_untax = self.convert_money(rec.amount_untaxed)

    @api.model
    def convert_money(self, amount):
        units = ['', 'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín']
        tens = ['', 'mười', 'hai mươi', 'ba mươi', 'bốn mươi', 'năm mươi', 'sáu mươi', 'bảy mươi', 'tám mươi', 'chín mươi']
        thousands = ['', 'nghìn', 'triệu', 'tỷ']

        def number_to_text(num):
            if num == 0:
                return 'không'
            cur_num = str(int(float(num)))
            length = len(cur_num)
            result = []
            
            groups = [cur_num[max(0, length - 3*(i+1)): length - 3*i] for i in range((length // 3) + 1) if cur_num[max(0, length - 3*(i+1)): length - 3*i]]
            groups.reverse()
            
            for idx, group in enumerate(groups):
                n = int(group)
                group_result = []
                
                if n >= 100:
                    group_result.append(units[n // 100] + " trăm")
                    n %= 100
                if n >= 20:
                    group_result.append(tens[n // 10])
                    n %= 10
                elif n >= 10:
                    group_result.append('mười')
                    n %= 10
                if n > 0:
                    group_result.append(units[n])
                
                if group_result:
                    result.append(" ".join(group_result) + " " + thousands[len(groups) - idx - 1])
            
            return " ".join(result).strip()
        
        label = number_to_text(amount).strip()

        return label[:1].upper() + label[1:].lower()

    @api.model
    def convert_vnd(self, amount):
        return f"{amount:,.0f}"

    @api.model
    def convert_usd(self, amount):
        return f"{amount:,.2f}"

    @api.model
    def convert_date(self, date):
        if date:
            return fields.Date.to_string(date)
        return ''

    @api.model
    def convert_print(self, date_value):
        if not date_value:
            return ""
        if isinstance(date_value, datetime):
            date_value = date_value.date()
        if isinstance(date_value, fields.Date):
            date_value = datetime.strptime(str(date_value), '%Y-%m-%d').date()
        return date_value.strftime('%d/%m/%Y')

    def get_report_purchaseorder_2025_docx_context(self):
        tz = pytz.timezone(self.env.user.tz)
        cur_date = datetime.now(tz)
        str_date = cur_date.strftime('%Hh%M ngày %d/%m/%Y')
        partner_bank_id = self.env['res.partner.bank'].sudo().search([('partner_id','=',self.partner_id.id)],limit=1)
        
        return {
            'acc_number':partner_bank_id.acc_number,
            'acc_holder_name':partner_bank_id.acc_holder_name if partner_bank_id.acc_holder_name else self.partner_id.name,
            'bank_name':partner_bank_id.bank_id.name,
        }
