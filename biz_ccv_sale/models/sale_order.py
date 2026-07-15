# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
import logging
import html2text
from bs4 import BeautifulSoup
from .component import vietnam_number
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    from docx import Document as Document
except ImportError:
    _logger.warning("`docx` Python module not found, Document file generation disabled. Consider installing this module if you want to generate Document files")
    Document = None


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_domain_sign_request(self):
        if self._context.get('params') and self._context.get('params').get('model') == 'sale.order':
            sale_id = self._context.get('params').get('id', False)
            sale_order = self.browse(sale_id).exists()
            if sale_order.sign_request_id:
                return [('id', 'in', sale_order.domain_sign_request.ids)]
        return [('sale_order_id', '=', False)]
    def _default_founder_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.founder_id')))
        if not user_find:
            user_find = self.env.user
        return user_find

    def _default_regional_head_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.regional_head_id')))
        return user_find

    @api.onchange('sales_team_captain_id')
    def onchange_sales_team_captain_id(self):
        for record in self:
            if record.sales_team_captain_id:
                record.regional_head_id = record.sales_team_captain_id

    def _default_finance_account_dept_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.finance_account_dept_id')))
        return user_find

    def _default_sale_manager_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.sale_manager_id')))
        return user_find

    def _default_bod_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.bod_id')))
        return user_find

    note_new = fields.Html('Note')
    old_order_code = fields.Char(string='Mã đơn cũ')
    founder_id = fields.Many2one('res.users', string="Founder", default=_default_founder_id)
    regional_head_id = fields.Many2one('res.users', string="Regional Head", default=_default_regional_head_id)
    finance_account_dept_id = fields.Many2one('res.users', string="Finance - Accounting Department", default=_default_finance_account_dept_id)
    sale_manager_id = fields.Many2one('res.users', string="Sales Manager", default=_default_sale_manager_id)
    bod_id = fields.Many2one('res.users', string="Board of Directors", default=_default_bod_id)
    code_contact = fields.Char(related="partner_id.code_contact", string='Contact Code', readonly=True,
                               required=True)
    transportation = fields.Char(string="Transportation")
    contact_representative = fields.Char(string="Representative", related="partner_id.representative")
    contact_phone = fields.Char(string="Contact phone number", related="partner_id.representative_phone")
    contact_total_due = fields.Monetary(string="Total Liabilities", related="partner_id.total_due")
    payment_time = fields.Char(string="Payment Time")
    sale_order_type_id = fields.Many2one(comodel_name="sale.order.type", string="Sale Order Type ID", copy=False, domain="[('company_id', '=', company_id)]")
    total_number_of_products = fields.Float(
        string="Total number of Products",
        compute='_compute_total_number_of_products',
        digits='Product Unit of Measure',
        store=True, precompute=True)
    total_amount_conversion = fields.Float(
        string="Total amount conversion",
        compute='_compute_amount_conversion',
        digits='Product Unit of Measure',
        store=True, precompute=True)
    total_product_uom_qty = fields.Float(
        string="Total quantity",
        compute='_compute_product_uom_qty',
        digits='Product Unit of Measure',
        store=True, precompute=True)
    total_qty_delivered = fields.Float(
        string="Total delivered",
        compute='_compute_qty_delivered',
        digits='Product Unit of Measure',
        store=True)
    order_state_id = fields.Many2one(comodel_name='res.country.state', string='Province/City', related='partner_id.state_id')

    domain_sign_request = fields.Many2many('sign.request', compute="_compute_domain_sign_request")
    sign_request_id = fields.Many2one(comodel_name="sign.request", string="Sign Request ID", domain=lambda self: self.get_domain_sign_request())
    sales_team_captain_id = fields.Many2one('res.users', 'Sales Team Captain', related="team_id.user_id", store=True)
    # sales_assistant_ids = fields.Many2many('res.users', 'sale_assistant_ids_rels', 'sales_ids', 'assisng_id','Sales Assistant')
    sales_assistant_ids = fields.Many2many(related="team_id.sales_assistant_ids")

    @api.constrains('sale_order_type_id')
    def check_sale_order_type_id(self):
        for record in self:
            if record.sale_order_type_id and record.company_id:
                if record.sale_order_type_id.company_id != record.company_id:
                    raise ValidationError(_("Current sales order type belongs to the company %s. Please choose another sale order type", record.sale_order_type_id.company_id.name))

    @api.onchange('user_id')
    def onchange_user_id(self):
        team_ids = []
        result = {'domain': {'team_id': []}}
        if self.user_id:
            team_ids = self.env['crm.team'].search([('member_ids','in',self.user_id.ids)])
            if self.team_id not in team_ids:
                self.team_id = False
        
        if team_ids:
            self.team_id = team_ids[0]
            result = {'domain': {'team_id': [('id', 'in', team_ids.ids)]}}
        return result

    @api.onchange('sign_request_id')
    def onchange_sign_request(self):
        if not self.sign_request_id:
            result = {'domain': {'sign_request_id': [('sale_order_id', '=', False)]}}
        else:
            result = {'domain': {'sign_request_id': [('id', 'in', self.domain_sign_request.ids)]}}
        return result

    def _compute_domain_sign_request(self):
        for record in self:
            record.domain_sign_request = self.env["sign.request"].search([('sale_order_id', '=', self.id)])

    @api.depends('order_line')
    def _compute_total_number_of_products(self):
        for record in self:
            record.total_number_of_products = len(record.order_line)

    @api.depends('order_line')
    def _compute_amount_conversion(self):
        for record in self:
            record.total_amount_conversion = sum(record.order_line.mapped("amount_conversion"))

    @api.depends('order_line')
    def _compute_product_uom_qty(self):
        for record in self:
            record.total_product_uom_qty = sum(record.order_line.mapped("product_uom_qty"))

    @api.depends('order_line', 'order_line.qty_delivered')
    def _compute_qty_delivered(self):
        for record in self:
            record.total_qty_delivered = sum(record.order_line.mapped("qty_delivered"))

    #=== CRUD METHODS ===#
    @api.model_create_multi
    def create(self, vals):
        records = super(SaleOrder, self).create(vals)
        for record in records:
            if record.sign_request_id and not record.sign_request_id.sale_order_id:
                record.sign_request_id.update({'sale_order_id': record.id})
        return records

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if 'sign_request_id' in vals:
            for record in self:
                if record.sign_request_id and not record.sign_request_id.sale_order_id:
                    record.sign_request_id.update({'sale_order_id': record.id})
                elif not record.sign_request_id:
                    if record.domain_sign_request:
                        sign_request_ids = record.domain_sign_request
                        sign_request_ids.update({'sale_order_id': False})
        return res

    # Report

    def get_phone(self):
        phone = ''
        list_phone = list()
        if self.partner_id:
            if self.partner_id.phone:
                list_phone.append(self.partner_id.phone)
            if self.partner_id.mobile:
                list_phone.append(self.partner_id.mobile)
            if self.partner_id.representative_phone:
                list_phone.append(self.partner_id.representative_phone)
            phone = '-'.join([phone for phone in list_phone])
        return phone

    def get_note(self):
        if self.note:
            soup = BeautifulSoup(self.note, 'lxml')
            soup_format = soup.prettify()
            html2_text = html2text.html2text(soup_format).replace('\\-', '-').replace('_', '').replace('#', '')
            note = '\n'.join([line for line in html2_text.splitlines() if line])
            if note:
                return "\n" + note
        return ''

    def get_internal_note(self):
        if self.internal_note:
            soup = BeautifulSoup(self.internal_note, 'lxml')
            result = soup.find_all('p')
            return '\n'.join([re.get_text('\t') for re in result])
        return ''

    def get_note_sale(self):
        company = self.env.company
        note_sale = company.note_sale
        if note_sale:
            soup = BeautifulSoup(note_sale, 'lxml')
            result = soup.find_all('p')
            return '\n'.join([re.get_text('\t') for re in result])
        return ''

    def get_noted_sale(self):
        company = self.env.company
        noted_sale = company.noted_sale
        if noted_sale:
            soup = BeautifulSoup(noted_sale, 'lxml')
            result = soup.find_all('p')
            return '\n'.join([re.get_text('\t') for re in result])
        return ''

    def get_sum_product_uom_qty(self):
        total = 0.0
        for line in self.order_line:
            total += line.product_uom_qty
        return total

    def get_sum_product_uom_qty_tan(self):
        total = 0.0
        for line in self.order_line:
            if line.product_uom.name in 'Tấn':
                total += line.product_uom_qty
        return total
    
    def get_sum_product_uom_qty_khac(self):
        total = 0.0
        for line in self.order_line:
            if line.product_uom.name not in 'Tấn':
                total += line.product_uom_qty
        return total

    def get_commitment_date_timezone(self):
        commitment_date = False
        if self.commitment_date:
            commitment_datetime = self.commitment_date
            user_tz = self.env.context.get('tz')
            if user_tz:
                commitment_datetime = pytz.utc.localize(commitment_datetime)
                commitment_datetime = commitment_datetime.astimezone(pytz.timezone(user_tz))
            commitment_date = commitment_datetime.date().strftime('%d/%m/%Y')
        return commitment_date
    
    def get_address(self):
        address_parts = []
        
        if self.partner_id.street:
            address_parts.append(self.partner_id.street)
        
        if self.partner_id.wards_id:
            address_parts.append(self.partner_id.wards_id.name) 
        
        if self.partner_id.district_id:
            address_parts.append(self.partner_id.district_id.name)
        
        if self.partner_id.state_id:
            address_parts.append(self.partner_id.state_id.name)
        
        if self.partner_id.country_id:
            address_parts.append(self.partner_id.country_id.name)

        full_address = ', '.join(address_parts)
        return full_address
    
    def get_report_saleorder_docx_context(self):
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
            'note_sale': self.get_note_sale(),
            'noted_sale': self.get_noted_sale(),
            'address': self.get_address(),
        }

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    amount_conversion = fields.Float('Amount Conversion', digits='Product Unit of Measure', readonly=True)
    conversion_unit = fields.Many2one('uom.uom', string='Conversion Unit')
    specification = fields.Char(string="Specification", compute="_compute_specification", store=False)
    is_promotional_product = fields.Boolean(string="Is Promotional Product", default=False)
    name_for_report = fields.Text(compute="_compute_name_for_report", store=True)
    packaging_image = fields.Binary(string="Packaging Image", copy=False)

    @api.onchange("product_template_id")
    def onchange_packaging_image(self):
        if self.product_template_id:
            self.packaging_image = self.product_template_id.packaging_image


    @api.depends("name")
    def _compute_name_for_report(self):
        for record in self:
            if record.name:
                split_string = record.name.split(" ")
                record.name_for_report = " ".join([re for re in split_string if not re.startswith("[") and not re.endswith("]")])
            else:
                record.name_for_report = False

    @api.depends('amount_conversion', 'conversion_unit')
    def _compute_specification(self):
        for record in self:
            if record.amount_conversion and record.conversion_unit:
                record.specification = f"{int(record.amount_conversion)} {record.conversion_unit.name}"
            else:
                record.specification = False

    @api.onchange('product_id')
    def change_conversion_unit(self):
        for res in self:
            res.conversion_unit = False
            if res.product_id and res.product_id.default_specification_id:
                res.conversion_unit = res.product_id.default_specification_id


    @api.onchange('product_uom_qty', 'conversion_unit','product_uom')
    def _onchange_amount_conversion(self):
        uom = self.product_uom
        conversion_uom = self.conversion_unit
        if uom:
            if uom.name == conversion_uom.name:
                self.amount_conversion = self.product_uom_qty
            elif conversion_uom.uom_type == 'reference':
                if uom.uom_type == 'smaller':
                    self.amount_conversion = self.product_uom_qty * uom.factor
                else:
                    self.amount_conversion = self.product_uom_qty / uom.factor
            elif conversion_uom.uom_type == 'smaller':
                if uom.uom_type == 'reference':
                    self.amount_conversion = self.product_uom_qty * conversion_uom.factor
                else:
                    self.amount_conversion = (self.product_uom_qty / uom.factor) * conversion_uom.factor
            elif conversion_uom.uom_type == 'bigger':
                if uom.uom_type == 'reference':
                    self.amount_conversion = conversion_uom.factor / self.product_uom_qty
                else:
                    self.amount_conversion = ((self.product_uom_qty * conversion_uom.factor) / uom.factor)






