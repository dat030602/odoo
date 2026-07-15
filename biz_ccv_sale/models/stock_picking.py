from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
import logging
import html2text
from bs4 import BeautifulSoup
from .component import vietnam_number
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import requests
from datetime import timedelta, datetime, time
import io
import requests
from PIL import Image
_logger = logging.getLogger(__name__)
try:
    from docx import Document as Document
except ImportError:
    _logger.warning("`docx` Python module not found, Document file generation disabled. Consider installing this module if you want to generate Document files")
    Document = None
from io import BytesIO
import barcode
from barcode.writer import ImageWriter

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.onchange('location_id', 'location_dest_id')
    def _onchange_locations(self):
        for record in self:
            location_id = record.location_id
            location_dest_id = record.location_dest_id

            record.move_line_ids.update({
                'location_id': location_id,
                'location_dest_id': location_dest_id
            })
        return super(StockPicking, self)._onchange_locations()
    
    def _default_voter_id(self):
        # user = self.env['res.users']
        # user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.voter_id')))
        user = self.env.user
        return user

    def _default_business_department_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.business_department_id')))
        return user_find

    def _default_chief_acc_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.chief_acc_id')))
        return user_find

    def _default_stocker_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.stocker_id')))
        return user_find

    def _default_unit_heads_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.unit_heads_id')))
        return user_find

    def _default_driver_consignee_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.driver_consignee_id')))
        return user_find

    def _default_load_department_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.load_department_id')))
        return user_find

    def _default_forklift_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.forklift_id')))
        return user_find

    def _default_supervision_department_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.supervision_department_id')))
        return user_find
    
    def _default_internal_control_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.internal_control_id')))
        return user_find

    def _default_delivery_person_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.delivery_person_id')))
        return user_find
    
    def _default_protect_service_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.protect_service_id')))
        return user_find
    
    def _default_carrier_person_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.carrier_person_id')))
        return user_find

    def _default_receipt_chief_accountant_id(self):
        user = self.env['res.users']
        user_find = user.browse(int(self.env['ir.config_parameter'].sudo().get_param('biz_ccv_sale.receipt_chief_accountant_id')))
        return user_find

    founder_id = fields.Many2one("res.users", string="Founder", related="sale_id.founder_id", store=False)
    regional_head_id = fields.Many2one("res.users", string="Regional Head", related="sale_id.regional_head_id", store=False)
    finance_account_dept_id = fields.Many2one("res.users", string="Finance - Accounting Department", related="sale_id.finance_account_dept_id", store=False)
    bod_id = fields.Many2one("res.users", string="Board of Directors", related="sale_id.bod_id", store=False)
    voter_id = fields.Many2one("res.users",string="Voter",default=_default_voter_id)
    business_department_id = fields.Many2one("res.users",string="Business Department",default=_default_business_department_id)
    chief_acc_id = fields.Many2one("res.users",string="Chief accountant",default=_default_chief_acc_id)
    stocker_id = fields.Many2one("res.users",string="Stocker",default=_default_stocker_id, tracking=True)
    unit_heads_id = fields.Many2one("res.users",string="Unit heads",default=_default_unit_heads_id)
    driver_consignee_id = fields.Many2one("res.users",string="Driver/Consignee",default=_default_driver_consignee_id)
    load_department_id = fields.Many2one("res.users",string="Loading and unloading department",default=_default_load_department_id)
    forklift_id = fields.Many2one("res.users",string="Forklift",default=_default_forklift_id)
    supervision_department_id = fields.Many2one("res.users",string="Supervision Department",default=_default_supervision_department_id)
    reason_output_input_stock = fields.Html('Reasons for import and export')
    number_of_implementers = fields.Integer('Number of Implementers')
    time_start = fields.Datetime(string='Start time', copy=False)
    time_end = fields.Datetime(string='End time', copy=False)
    total_time_vehicle = fields.Integer(string='Total vehicle departure time', compute='compute_total_time_vehicle', copy=False, store=True, readonly=False)
    attention = fields.Html('Attention')
    export_at_ware = fields.Html('Export to warehouse (batch compartment)')
    location_export = fields.Html('Location')

    delivery_person_id = fields.Many2one("res.users","Delivery person", default=_default_delivery_person_id)
    protect_service_id = fields.Many2one("res.users",'Protect service', default=_default_protect_service_id)
    implementing_unit = fields.Char("Implementing unit")
    carrier_person_id = fields.Many2one("res.users",'Carrier', default=_default_carrier_person_id)
    receipt_chief_accountant_id = fields.Many2one("res.users",'Kế toán trưởng', default=_default_receipt_chief_accountant_id)
    internal_control_id = fields.Many2one("res.users", 'Internal control', default=_default_internal_control_id)

    @api.onchange('number_of_implementers')
    def onchange_number_of_implementers(self):
        for rec in self:
            if rec.number_of_implementers < 0:
                raise ValidationError(_("Please enter a number greater than or equal to 0"))

    @api.onchange('time_start')
    def onchange_time_start(self):
        for rec in self:
            if rec.time_end:
                if rec.time_start:
                    if rec.time_start > rec.time_end:
                        raise ValidationError(_("Start time must be less than end time"))

    @api.onchange('time_end')
    def onchange_time_end(self):
        for rec in self:
            if rec.time_start:
                if rec.time_end:
                    if rec.time_end < rec.time_start:
                        raise ValidationError(_("End time must be greater than start time"))

    @api.depends('time_start', 'time_end')
    def compute_total_time_vehicle(self):
        for rec in self:
            rec.total_time_vehicle = False
            if rec.time_start and rec.time_end:
                result = (rec.time_end - rec.time_start).total_seconds() / 60
                rec.total_time_vehicle = int(result)


    def get_reason_output_input_stock(self):
        if self.reason_output_input_stock:
            soup = BeautifulSoup(self.reason_output_input_stock, 'lxml')
            soup_format = soup.prettify()
            html2_text = html2text.html2text(soup_format).replace('\\-', '-').replace('_', '').replace('#', '')
            note = '\n'.join([line for line in html2_text.splitlines() if line])
            if note:
                return note
        return ''

    def product_uom_qty_move_ids_without_package(self):
        total = 0
        if self.move_ids_without_package:
            for move in self.move_ids_without_package:
                move._compute_product_uom_qty_float()
            total = sum(self.move_ids_without_package.mapped('product_uom_qty'))

        if total != 0:
            total = str('{:,.3f}'.format(total)).replace(".", ",")
        return total


    def bag_number_move_ids_without_package(self):
        total = 0
        if self.move_ids_without_package:
            total = sum(self.move_ids_without_package.mapped('bag_number'))
        return total

    def get_scheduled_date(self):
        return self.scheduled_date and (self.scheduled_date + timedelta(hours=7)).strftime('Ngày %d tháng %m năm %Y') or 'Ngày.....tháng.....năm.....'

    def get_stock_date_receipt(self):
        return self.stock_date_receipt and (self.stock_date_receipt + timedelta(hours=7)).strftime('Ngày %d tháng %m năm %Y') or 'Ngày.....tháng.....năm.....'

    def get_date_done(self):
        return self.date_done and self.date_done.strftime('Ngày %d tháng %m năm %Y') or 'Ngày.....tháng.....năm.....'

    def get_time_start(self):
        if self.time_start:
            return (self.time_start + timedelta(hours=7)) and (self.time_start + timedelta(hours=7)).strftime('%d-%m-%Y %H:%M:%S')
        else:
            return '.........................'

    def get_time_end(self):
        if self.time_end:
            return (self.time_end + timedelta(hours=7)) and (self.time_end + timedelta(hours=7)).strftime('%d-%m-%Y %H:%M:%S')
        else:
            return '...............................'

    def get_number_of_implementers(self):
        return self.number_of_implementers or '.................'

    def get_total_time_vehicle(self):
        return self.total_time_vehicle or '.................'

    def get_attention(self):
        company = self.env.company
        note_stock = company.note_stock
        if note_stock:
            soup = BeautifulSoup(note_stock, 'lxml')
            result = soup.find_all('p')
            return 'Lưu ý: ' + '\n'.join([re.get_text('\t') for re in result])
        return ''

    def get_export_at_ware(self):
        if self.export_at_ware:
            soup = BeautifulSoup(self.export_at_ware, 'lxml')
            result = soup.find_all('p')
            return '\n'.join([re.get_text('\t') for re in result])
        return '............................'

    def get_location_export(self):
        if self.location_export:
            soup = BeautifulSoup(self.location_export, 'lxml')
            result = soup.find_all('p')
            return '\n'.join([re.get_text('\t') for re in result])
        return '.............................'

    def get_partner(self):
        if self.partner_id:
            if not self.partner_id.parent_id:
                return self.partner_id.name
            if self.partner_id.parent_id:
                return self.partner_id.parent_id.name

    def get_property_stock_account(self,check_debit=False):
        debit_new = []
        has_new = []
        if self.state == 'done':
            scraps = self.env['stock.scrap'].search([('picking_id', '=', self.id)])
            valuation_layers = (self.move_ids + scraps.move_id).stock_valuation_layer_ids
            for layer in valuation_layers:
                for line in layer.account_move_id.line_ids:
                    if check_debit and line.debit > 0:
                        debit_new.append(line.account_id and line.account_id.code or '')
                    if not check_debit and line.credit > 0:
                        has_new.append(line.account_id and line.account_id.code or '')
        else:
            for move in self.move_ids_without_package.filtered(lambda x: x.product_id.categ_id != False):
                if check_debit and move.product_id.categ_id.property_stock_account_output_categ_id:
                    debit_new.append(move.product_id.categ_id.property_stock_account_output_categ_id.code or move.product_id.categ_id.property_stock_account_output_categ_id.code)
                if not check_debit and move.product_id.categ_id.property_stock_valuation_account_id:
                    has_new.append(move.product_id.categ_id.property_stock_valuation_account_id.code or move.product_id.categ_id.property_stock_valuation_account_id.code)
        if check_debit:
            result = set(debit_new)
            debit = ', '.join([re for re in result])
            return debit or ''
        else:
            result = set(has_new)
            has = ', '.join([re for re in result])
            return has or ''

    def get_name_user(self,user):
        if user == 'voter':
            return self.voter_id and self.voter_id.name or ''
        if user == 'business_department':
            return self.business_department_id and self.business_department_id.name or ''
        if user == 'chief_acc':
            return self.chief_acc_id and self.chief_acc_id.name or ''
        if user == 'stocker':
            return self.stocker_id and self.stocker_id.name or ''
        if user == 'unit_heads':
            return self.unit_heads_id and self.unit_heads_id.name or ''
        if user == 'driver_consignee':
            return self.driver_consignee_id and self.driver_consignee_id.name or ''
        if user == 'load_department':
            return self.load_department_id and self.load_department_id.name or ''
        if user == 'forklift':  
            return self.forklift_id and self.forklift_id.name or ''
        if user == 'supervision_department':
            return self.supervision_department_id and self.supervision_department_id.name or ''
 
    def covert_url_to_binary(self):   
        image_bytes = False
        try:
            if self.barcode:
                barcode_instance = False
                barcode_class = False
                try:
                    from barcode import Code128
                    barcode_instance = Code128(self.barcode, writer=ImageWriter())
                except ImportError:
                    barcode_class = barcode.get_barcode_class('code128')
                    barcode_instance = barcode_class(self.barcode, writer=ImageWriter())
                buffer = io.BytesIO()
                barcode_instance.write(buffer, {'module_height': 15.0, 'font_size': 0, 'module_width': 0.4, 'text_distance': 4.0})
                buffer.seek(0)
                image_data = buffer.getvalue()
                image_bytes = base64.b64encode(image_data).decode('utf-8')
        except:
            image_bytes = False
        return image_bytes 

    def format_decimal(self, number):
        if not number:
            return 0
        string = '{:,.3f}'.format(number).split('.')
        return '%s,%s' % (string[0].replace(',','.'), string[1])

    def get_delivery_user_name(self):
        delivery_user_name = ''
        if self.mrp_production_id:
            delivery_user_name = self.mrp_production_id.user_id.name_without_position
        elif self.partner_id:
            delivery_user_name = self.partner_id.name
        return delivery_user_name

    def _get_sign_if_approved(self, user):
        if not user or not self.sale_id:
            return False
        approved = self.env['sale.sign.requests'].sudo().search([
            ('sale_order_id', '=', self.sale_id.id),
            ('state', '=', 'approved'),
        ], limit=1)
        return user.sudo().sign_signature if approved else False

    def get_report_stock_docx_context(self):
        return {
            'stockpicking': self,
            'partner': self.get_partner(),
            'scheduled_date': self.get_stock_date_receipt(),
            'stock_date_receipt': self.get_stock_date_receipt(),
            'reason': self.get_reason_output_input_stock(),
            'product_uom_qty': self.product_uom_qty_move_ids_without_package(),
            'bag_number': self.bag_number_move_ids_without_package(),
            'quantity_done': self.move_ids_without_package and sum(move.quantity_done for move in self.move_ids_without_package) or 0,
            'bag_done': self.move_ids_without_package and sum(move.bag_done for move in self.move_ids_without_package) or 0,
            'debit': self.get_property_stock_account(check_debit=True),
            'has': self.get_property_stock_account(check_debit=False),
            'voter': (self.founder_id.sudo().name_without_position or self.founder_id.name) if self.founder_id else '',
            'business_department': (self.regional_head_id.sudo().name_without_position or self.regional_head_id.name) if self.regional_head_id else '',
            'chief_acc': (self.finance_account_dept_id.sudo().name_without_position or self.finance_account_dept_id.name) if self.finance_account_dept_id else '',
            'stocker': self.get_name_user(user='stocker'),
            'unit_heads': (self.bod_id.sudo().name_without_position or self.bod_id.name) if self.bod_id else '',
            'driver_consignee': self.get_name_user(user='driver_consignee'),
            'load_department': self.get_name_user(user='load_department'),
            'forklift': self.get_name_user(user='forklift'),
            'supervision_department': self.get_name_user(user='supervision_department'),
            'image_barcode': self.covert_url_to_binary(),
            'numofimple': self.get_number_of_implementers(),
            'start': self.get_time_start(),
            'end': self.get_time_end(),
            'total': self.get_total_time_vehicle(),
            'attention': self.get_attention(),
            'export_at_ware': self.get_export_at_ware(),
            'location_export': self.get_location_export(),
            'date_done': self.get_date_done(),
            'format_decimal': self.format_decimal,
            'get_user_name': self.get_delivery_user_name(),
            'voter_sign': self._get_sign_if_approved(self.founder_id),
            'business_department_sign': self._get_sign_if_approved(self.regional_head_id),
            'chief_acc_sign': self._get_sign_if_approved(self.finance_account_dept_id),
            'unit_heads_sign': self._get_sign_if_approved(self.bod_id),
        }