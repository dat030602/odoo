# -*- coding: utf-8 -*-

from asyncore import write
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from urllib.parse import urlencode
from odoo.addons.web.controllers.main import xml2json_from_elementtree
from datetime import datetime
import base64

import random
import hashlib
import pprint
import json
import requests
import logging
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)

ADJUSTMENT_INVOICE_TYPE = [
    ('1', 'Replacement'),
    ('2', 'Adjust increase'),
    ('3', 'Adjust decrease'),
    ('4', 'Adjust information')
]

PAYMENT_METHOD = {
    'TM/CK': 'TM/CK',
    'tien-mat': 'Tiền mặt',
    'TM': 'TM',
    'CK': 'CK',
    'chuyen-khoan': 'Chuyển khoản',
    'can-tru-cong-no': 'Cấn trừ công nợ',
    'tra-hang': 'Trả hàng',
}

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
}

TIMEOUT = 5

API_URL = "https://ehoadondientu.com/MyService.asmx"


class VinhHyEInvoice(models.Model):
    _name = "vinhhy.einvoice"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Vinh Hy E-Invoice"
    _order = "id desc"

    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id or self.env.user.company_id.currency_id

    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [('company_id', '=', company_id)]
        company_currency_id = self.env['res.company'].browse(company_id).currency_id.id
        currency_id = self._context.get('default_currency_id') or company_currency_id
        currency_domain = [('currency_id', '=', currency_id)]
        if currency_id == company_currency_id:
            currency_domain = ['|', ('currency_id', '=', False)] + currency_domain
        return (
                self.env['account.journal'].search(domain + currency_domain, limit=1)
                or self.env['account.journal'].search(domain, limit=1)
        )
    
    @api.model
    def _get_default_team(self):
        return self.env['crm.team']._get_default_team_id()

    def generateFkey(self):
        strsequence = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        idrand = ''
        for x in range(13):
            idrand += random.choice(strsequence)
        exist_fkey = self.search([('vh_einv_fkey','=',idrand)])
        if len(exist_fkey) > 1:
            return self.generateFkey()
        else:
            return idrand

    name = fields.Char(default='New', tracking=True, related='invoice_no', store=True, copy=False)
    invoice_no = fields.Char('Invoice No', default='/', copy=False)
    invoice_ids = fields.Many2many('account.move', 'vh_einv_account_move_rel', 'vh_einv_id','move_id', string='Odoo Invoices', domain=[('move_type','=','out_invoice')])
    sale_ids = fields.Many2many('sale.order', 'vh_einv_sale_order_rel', 'vh_einv_id','sale_id', string='Odoo Sale Order', domain=[('state','in',['sale','done'])])
    user_id = fields.Many2one('res.users', string='User', readonly=True, default=lambda self: self.env.user, copy=False, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('account.move'))
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True,
        default=_default_currency, tracking=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True,
        default=_default_journal, domain="[('company_id', '=', company_id)]")
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency", readonly=True)
    partner_id = fields.Many2one('partner.vat', 'VH E-Invoice Contact', tracking=True)
    partner_vat_id = fields.Many2one('partner.vat', 'Legal VH E-Invoice Company', tracking=True, domain="[('company_type','=','company')]")
    # Customer Information
    customer_name = fields.Char('Contact Name', compute='_compute_customer_info', store=True)
    legal_customer_name = fields.Char('VH E-Invoice Customer Name', compute='_compute_customer_info', store=True)
    customer_code = fields.Char('Customer Code', compute='_compute_customer_info', store=True)
    customer_vat = fields.Char('VAT', compute='_compute_customer_info', store=True, tracking=True)
    customer_address = fields.Char('VAT Address', compute='_compute_customer_info', store=True, readonly=False)
    customer_email = fields.Char('Customer Emails', tracking=True)
    is_individual_customer = fields.Boolean()
    vh_inv_tax_id = fields.Many2one('einvoice.tax', string='VAT', compute='_compute_vat', store=True, tracking=True)
    date_invoice = fields.Date(string='Invoice Date', index=True, copy=False)
    vh_inv_template_id  = fields.Many2one('vinhhy.einvoice.template', 'Config Template')
    template_code = fields.Char('Template Code', related='vh_inv_template_id.template_code', store=True)
    invoice_series = fields.Char('Invoice Series', related='vh_inv_template_id.series', store=True)
    payment_method = fields.Selection([
        ('TM/CK', 'TM/CK'),
        ('tien-mat', 'Tiền mặt'),
        ('TM', 'TM'),
        ('CK', 'CK'),
        ('chuyen-khoan', 'Chuyển khoản'),
        ('can-tru-cong-no', 'Cấn trừ công nợ'),
        ('tra-hang', 'Trả hàng'),
        ], string='Payment Method', copy=False, default='TM', tracking=True)
    lookup_code = fields.Char('Lookup Code', readonly=True, copy=False)
    vh_einv_key = fields.Char('Invoice Key', readonly=True, copy=False)
    vh_einv_fkey = fields.Char('Invoice fKey', readonly=True, copy=False)
    state = fields.Selection([
        ('N','Draft'),
        ('XN','Confirm to Issue'),
        ('M','New'),
        ('CM', 'Issued'),
        ('H','Canceled')
    ], default='N', copy=False)
    einv_type = fields.Selection([
        ('origin', 'Origin'),
        ('is_replaced', 'Is Replaced'),
        ('is_adjusted', 'Is Adjusted'),
        ('replacement_invoice', 'Replacement Invoice'),
        ('adjustment_invoice', 'Adjustment Invoice'),
    ], default='origin', string='E-Invoice Type', copy=False)
    adjustmentInvoiceType = fields.Selection(ADJUSTMENT_INVOICE_TYPE, string='Adjustment Invoice Type', default=False, copy=False)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, copy=False, compute='_compute_amount', tracking=True)
    amount_tax = fields.Monetary(string='Tax', store=True, readonly=True, copy=False, compute='_compute_amount', tracking=True)
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, copy=False, compute='_compute_amount', tracking=True)
    amount_discount = fields.Monetary(string='Discount Amount', store=True, readonly=True, compute='_compute_amount', copy=False, tracking=True)
    notes = fields.Text(string="Note")
    user_id = fields.Many2one('res.users', string='User', readonly=True, default=lambda self: self.env.user, copy=False, tracking=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', ondelete='set null', default=_get_default_team, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True)
    reason_adjust_einv = fields.Char(string='Reason Adjust', copy=False)
    related_inv_ids = fields.One2many('vinhhy.einvoice', 'base_einv_id', copy=False)
    base_einv_id = fields.Many2one('vinhhy.einvoice', string='Base Vinh Hy E-Invoice', copy=False)
    # infomation cancel/adjust inv
    seller_responsible = fields.Many2one('res.users', string='Seller Responsible')
    seller_position = fields.Char(string='Seller Position')
    seller_address = fields.Char(string='Seller Address')
    buyer_responsible = fields.Many2one('partner.vat', string='Buyer Responsible')
    buyer_position = fields.Char(string='Buyer Position')
    buyer_address = fields.Char(string='Buyer Address')
    line_ids = fields.One2many('vinhhy.einvoice.line', 'vh_inv_id', copy=True)
    is_update_vat_prod_qty = fields.Boolean(default=False, copy=False)
    inv_attachment_ids = fields.Many2many('ir.attachment', 'vh_einv_ir_attachments_rel', 'vh_einv', 'attachment_id',
        string='Attachments', copy=False)

    def comfirm_2_issue(self):
        self.write({
            'invoice_no': self.env['ir.sequence'].next_by_code('vinhhy.einvoice.sequence'),
            'state': 'XN'
        })
    
    def unlink(self):
        for invoice in self:
            if invoice.state != 'N' and not self.env.user.has_group('base.group_system'):
                raise UserError(_('You can not delete the invoice not in draft state!'))
            # if invoice.state not in ['N','XN']:
            #     raise UserError(_('Invoice status is not allowed to delete!'))
        return super(VinhHyEInvoice, self).unlink()

    @api.onchange('user_id')
    def onchange_user_id(self):
        if self.user_id:
            self.team_id = self.env['crm.team'].with_context(
                default_team_id=self.team_id.id
            )._get_default_team_id(user_id=self.user_id.id)

    @api.depends('line_ids', 'line_ids.price_subtotal', 'line_ids.price_tax', 'line_ids.price_discount' )
    def _compute_amount(self):
        for s in self:
            s.amount_untaxed = round(sum(line.price_subtotal for line in s.line_ids), 0)
            s.amount_tax = round(sum(line.price_tax for line in s.line_ids), 0)
            s.amount_total = s.amount_untaxed + s.amount_tax
            s.amount_discount = round(sum(line.price_discount for line in s.line_ids), 0)

    @api.depends('line_ids.vh_inv_line_tax_id')
    def _compute_vat(self):
        if self.line_ids:
            self.vh_inv_tax_id = self.line_ids[0].vh_inv_line_tax_id
        else:
            self.vh_inv_tax_id = False

    @api.depends('partner_id', 'partner_vat_id')
    def _compute_customer_info(self):
        for s in self:
            s.customer_name = s.partner_id.name or False
            s.legal_customer_name = s.partner_vat_id.name or False
            if s.partner_vat_id:
                s.is_individual_customer = False
                s.customer_vat = s.partner_vat_id.vat or False
                s.customer_code = s.partner_vat_id.ref or False
                s.customer_address = s.partner_vat_id.partner_address or ''
            elif s.partner_id:
                s.is_individual_customer = True
                s.customer_vat = s.partner_id.vat or ''
                s.customer_code = s.partner_id.ref or ''
                s.customer_address = s.partner_id.partner_address or ''
            else:
                s.customer_vat = ''
                s.customer_address = ''
            if not s.fiscal_position_id:
                if s.partner_vat_id and s.partner_vat_id.partner_id:
                    s.fiscal_position_id = s.partner_vat_id.partner_id.property_account_position_id
                elif s.partner_id and s.partner_id.partner_id:
                    s.fiscal_position_id = s.partner_id.partner_id.property_account_position_id
                else:
                    False

    
    def vh_einv_send_request(self, endpoint, method, params, timeout=TIMEOUT):
        try:
            if method.upper() in ('GET', 'DELETE'):
                res = requests.request(method.lower(), API_URL + endpoint, params=params, timeout=timeout)
            elif method.upper() in ('POST', 'PATCH', 'PUT'):
                res = requests.request(method.lower(), API_URL + endpoint, data=params, headers=HEADERS, timeout=timeout)
            else:
                raise Exception(_('Method not supported [%s] not in [GET, POST, PUT, PATCH or DELETE]!') % (method))
            res.raise_for_status()
            status = res.status_code
            root = ET.fromstring(res.content.decode('utf-8'))
            json_data = xml2json_from_elementtree(root)
            response = json_data.get('children')[0]
        except requests.HTTPError as error:
            if error.response.status_code in (204, 404):
                status = error.response.status_code
                response = ""
            else:
                _logger.exception("Bad request : %s !", error.response.content)
                raise error
        return (status, response)

    def _prepare_inv_line_val(self):
        val = []
        for line in self.line_ids:
            val.append({
                'Ma_hang': line.vat_product_id.vat_code,
                'Ten_hang': line.vat_product_id.name,
                'Dvt': line.uom_id.name,
                'So_luong': line.quantity,
                'Gia': line.price_unit,
                'Tien': line.price_subtotal_signed,
                'Thue_suat': int(line.vh_inv_line_tax_id.amount),
                'Thue': line.price_tax,
                'Ty_le_chiet_khau': line.discount,
                'chiet_khau': line.price_discount,
                'km':'',
                'so_lo':'',
                'han_dung':''
            })
        return val
        # TEST VALUE
        # return [
        #     {
        #         'Ma_hang':'A001',
        #         'Ten_hang':'Xe dưới 12 ghế, xe tải có tải trọng dưới 2 tấn',
        #         'Dvt':'lượt',
        #         'So_luong':1,
        #         'Gia':31818,
        #         'Tien':31818,
        #         'Thue_suat':10,
        #         'Thue':3182,
        #         'Ty_le_chiet_khau':0,
        #         'chiet_khau':0,
        #         'km':'',
        #         'so_lo':'',
        #         'han_dung':''
        #     }
        # ]

    def _prepare_einv_data(self):
        val ={}
        if len(self.line_ids) < 1:
            raise UserError(_('No invoice items for issuing invoice!'))
        if self.vh_einv_fkey:
            val.update({"fkey": self.vh_einv_fkey})
        else: 
            fkey = self.generateFkey()
            self.update({'vh_einv_fkey': fkey})
            val.update({"fkey": self.vh_einv_fkey})
        val.update({
            'Ngay_hd': self.date_invoice.strftime("%Y-%m-%d") if self.date_invoice else fields.Date.today().strftime("%Y-%m-%d"),
            'Ky_hieu_mau': self.template_code,
            'So_seri': self.invoice_series,
            'So_hd': str(self.invoice_no),
            # customer info
            'Mst': self.customer_vat or '',
            'Ten_cty': self.legal_customer_name or '',
            'Dia_chi': self.customer_address or '',
            'Email': self.customer_email or '',
            'Tel': self.partner_vat_id.phone or '' if self.partner_vat_id else self.partner_id.phone or '',
            'so_tk':'',
            'Nguoi_mua_hang': self.customer_name or '',
            'hinh_thuc_thanh_toan': PAYMENT_METHOD.get(self.payment_method, ''),
            'Ma_tte': self.currency_id.name or '',
            'Ty_gia': self.currency_id.inverse_rate or 0,
        })
        return val

    # send origin inv
    def action_send_to_issue_vh_einv(self):
        if self.einv_type == 'origin':
            return self.action_send_orgin_vh_einv()
        # elif self.einv_type in ['replacement_invoice','adjustment_invoice']:
        #     return self.action_send_adjust_replace_vh_einv()
    
    # def action_send_adjust_replace_vh_einv(self):
    #     if not self.company_id or not self.company_id.vinhhy_einv_username or not self.company_id.vinhhy_einv_password:
    #         raise UserError(_("Please input Vinh Hy E-Invoice account!"))
    #     data = {
    #         'user': self.company_id.vinhhy_einv_username,
    #         'pwd': self.company_id.vinhhy_einv_password,
    #         'thongtin': {
    #             'Fkey': self.base_einv_id.vh_einv_key or '',
    #             'nguoidaidien_benban': self.seller_responsible.name or '',
    #             'chucvu_nguoidaidien_benban': self.seller_position or '',
    #             'diachi_nguoidaidien_benban': self.seller_address or '',
    #             'nguoidaidien_benmua': self.buyer_responsible.name or '',
    #             'chucvu_nguoidaidien_benmua': self.buyer_position or '',
    #             'diachi_nguoidaidien_benmua': self.buyer_address or '',
    #             'ly_do': self.reason_adjust_einv or '',
    #             'email': self.customer_email or '',
    #             'Loai': self.adjustmentInvoiceType or ''
    #         },
    #     }
    #     einv_data = self._prepare_einv_data()
    #     lines_val = self._prepare_inv_line_val()
    #     data['data'] = {**einv_data, **{'Chitiet': lines_val}}
    #     result = self.vh_einv_send_request('/adjustReplaceInvoice', 'post', urlencode(data))
    #     if result[0] == 200: #gửi request thành công
    #         self.message_post(body='Gửi hóa đơn tùy chỉnh thành công. <br/> Kết quả: %s' %result[1])
    #         res_data = result[1].split('-')
    #         inv_no = res_data[2] if res_data[2] else ''
    #         einv_state = res_data[3] if res_data[3] else ''
    #         lookup_code = res_data[4] if res_data[4] else ''
    #         vh_einv_key = res_data[5] if res_data[5] else ''
    #         data_update = {}
    #         if inv_no:
    #             data_update.update({
    #                 'name': inv_no,
    #                 'state': 'CM'
    #             })
    #         if einv_state:
    #             data_update.update({
    #                 'state': einv_state
    #             })
    #         if lookup_code:
    #             data_update.update({
    #                 'lookup_code': lookup_code,
    #             })
    #         if vh_einv_key:
    #             data_update.update({
    #                 'vh_einv_key': vh_einv_key,
    #             })
    #         if data_update:
    #             self.write(data_update)
    #         # cập nhật lại loại hóa đơn gốc
    #         if self.einv_type == 'replacement_invoice':
    #             self.base_einv_id.write({'einv_type': 'is_replaced'})
    #         if self.einv_type == 'adjustment_invoice':
    #             self.base_einv_id.write({'einv_type': 'is_adjusted'})
    #     else:
    #         self.message_post(body=result[1])
    #         raise UserError('Xảy ra lỗi khi phát hành hóa đơn!')

    def action_update_vat_product_quantity(self):
        if self.is_update_vat_prod_qty: #hóa đơn đã cập nhật số lượng tồn kho cho sản phẩm rồi không cập nhật lại
            return True
        for line in self.line_ids:
            line.vat_product_id.write({
                'qty_available': line.vat_product_id.qty_available - line.quantity
            })
        self.is_update_vat_prod_qty = True

    def action_send_orgin_vh_einv(self):
        if not self.company_id or not self.company_id.vinhhy_einv_username or not self.company_id.vinhhy_einv_password:
            raise UserError(_("Please input Vinh Hy E-Invoice account!"))
        data = {
            'user': self.company_id.vinhhy_einv_username,
            'pwd': self.company_id.vinhhy_einv_password,
        }
        einv_data = self._prepare_einv_data()
        lines_val = self._prepare_inv_line_val()
        data['data'] = {**einv_data, **{'Chitiet': lines_val}}
        _logger.info(data)
        result = self.vh_einv_send_request('/importInvoice', 'post', urlencode(data))
        if result[0] == 200: #gửi request thành công
            try:
                res_json =  json.loads(result[1].replace('\n',''))[0]
                if res_json.get('ma', '') == "Ok": #kết quả thành công
                    res_detail = res_json.get('mota', '').split('-')
                    inv_no = res_detail[2] if res_detail[2] else ''
                    lookup_code = res_detail[3] if res_detail[3] else ''
                    vh_einv_key = res_detail[4] if res_detail[4] else ''
                    if inv_no:
                        self.write({
                            "name": inv_no,
                        })
                        self.message_post(body="Gửi hóa đơn thành công! <br/>.")
                    if lookup_code:
                        self.write({"lookup_code": lookup_code})
                    if vh_einv_key:
                        self.write({"vh_einv_key": vh_einv_key})
                    # # nếu trả về mã tra cứu và khóa và KHÔNG CÓ shđ -> trạng thái chưa cấp mã
                    # if lookup_code and vh_einv_key and not inv_no:
                    #     self.write({'state': 'M'})
                    #     self.message_post(body="Gửi hóa đơn đơn thành công! <br/> Hóa đơn chưa được cấp mã.")
                    # lấy trạng thái hóa đơn
                    self.action_vh_einv_get_number()
                else:
                    body_msg= "Xảy ra lỗi khi gửi hóa đơn."
                    if res_json.get('mota', ''):
                        body_msg += '<br/>' + res_json.get('mota', '')
                    self.message_post(body=body_msg)
            except Exception as e:
                raise UserError(str(e) + '\nKết quả phát hành: %s' %str(result))
        else:
            self.message_post(body=result[1])
            raise UserError('Xảy ra lỗi khi phát hành hóa đơn!')
    
    def action_vh_einv_get_number(self):
        if not self.company_id or not self.company_id.vinhhy_einv_username or not self.company_id.vinhhy_einv_password:
            raise UserError(_("Please input Vinh Hy E-Invoice account!"))
        if not self.lookup_code:
            raise UserError(_("Lookup code is required to get invoice number!"))
        data = {
            'user': self.company_id.vinhhy_einv_username,
            'pwd': self.company_id.vinhhy_einv_password,
            'matracuu': self.lookup_code,
            'key': self.vh_einv_key or '',
        }
        result = self.vh_einv_send_request('/getInvoiceNumber', 'post', urlencode(data))
        #response 1-C22TYY-<so hd>-M-3RZUPSJ4-5300000394
        if result[0] == 200:
            self.message_post(body='Lấy số hóa đơn thành công. <br/> Kết quả: %s' %result[1])
            res_data = result[1].split('-')
            if res_data and res_data[2]:
                self.write({
                    'invoice_no': res_data[2],
                    'state': res_data[3]
                })
            # cập nhật số lượng tồn kho cho sản phẩm
            if self.state == 'CM':
                self.action_update_vat_product_quantity()
        else:
            self.message_post(body='Xảy ra lỗi khi lấy số hóa đơn.<br/> %s' %result[1])

    def action_vh_einv_cancel(self):
        related_inv = self.related_inv_ids.filtered(lambda inv: inv.state not in ['N','H'])
        if len(related_inv) > 0:
            raise UserError(_('Cancellation is only allowed when related invoices are in Draft or Canceled status'))
        reason_adjust_einv = self.env.context.get('reason_adjust_einv', False)
        if not reason_adjust_einv:
            raise UserError(_('A reason for cancellation is required.'))
        self.write({
            'seller_responsible': self.env.context.get('seller_responsible', ''),
            'seller_position': self.env.context.get('seller_position', ''),
            'buyer_responsible': self.env.context.get('buyer_responsible', ''),
            'buyer_position': self.env.context.get('buyer_position', ''),
            'reason_adjust_einv': reason_adjust_einv,
        })
        if self.state == 'N':
            self.update({
                'state': 'H'
            })
            return True
        if not self.vh_einv_key:
            raise UserError(_('Can not find key of e-invoice to cancel!'))
        if self.state not in ['N','M','CM']:
            raise UserError(_('Invoice status is not allowed to cancel!'))
        # cập nhật thông tin cho hóa đơn bị hủy
        data = {
            'user': self.company_id.vinhhy_einv_username,
            'pwd': self.company_id.vinhhy_einv_password,
            'matracuu': self.lookup_code, 
            'key': self.vh_einv_key,
            'nguoi_dai_dien_ban': self.seller_responsible.name or '',
            'chucvu_ban': self.seller_position or '',
            'nguoi_dai_dien_mua': self.buyer_responsible.name or '',
            'chucvu_mua': self.buyer_position or '',
            'ly_do': self.reason_adjust_einv or '',
            'email': self.customer_email or ''
        }
        result = self.vh_einv_send_request('/cancelInvoice', 'post', urlencode(data))
        if result[0] == 200:
            res_json =  json.loads(result[1].replace('\n',''))[0]
            if res_json.get('ma', '') == "Ok":
                self.write({
                    'state': 'H'
                })
                self.message_post(body="Hủy hóa đơn thành công" + '<br/>' + str(res_json))
            else:
                body_msg= "Xảy ra lỗi khi hủy hóa đơn."
                if res_json.get('mota', ''):
                    body_msg += '<br/>' + res_json.get('mota', '')
                self.message_post(body=body_msg)
        else:
            self.message_post(body='Xảy ra lỗi khi hủy hóa đơn.<br/> %s' %result[1])

    def action_get_einv_pdf(self):
        result = self.vh_einv_send_request('/getInvoicePdf', 'post', urlencode({'mahoadon': self.lookup_code and self.lookup_code or ''}))
        try:
            if result[0] != 200:
                raise UserError('Xảy ra lỗi khi tải file PDF\n%s' %result)
            else:
                filename = self.name or 'file' + '.pdf'
                attachment = {
                    'name': filename,
                    'datas': base64.encodebytes(bytes.fromhex(result[1])),
                    'res_model': 'vinhhy.einvoice',
                    'res_id': self.id,
                    'type': 'binary',
                }
                attachment_id = self.env['ir.attachment'].create(attachment)
                self.inv_attachment_ids.unlink()
                self.write({
                    'inv_attachment_ids': [(6, 0, [attachment_id.id])]
                })
        except Exception as e:
            _logger.info('=========================Exception when executing the pdf file: %s' % e)

    def action_open_invoice(self):
        self.ensure_one()
        view = self.env.ref('vinhhy_einvoice_service.vinhhy_einvoice_form')
        return {
            'name': _('Vinh Hy E-Invoice'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'vinhhy.einvoice',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': self.id,
            'context': dict(self.env.context, create=False)
        }

    def action_get_invoice_status(self):
        data = {
            'mahoadon': self.lookup_code and self.lookup_code or ''
        }
        result = self.vh_einv_send_request('/getInvoiceStatus', 'post', urlencode(data))
        if result[0] == 200:
            res_json =  json.loads(result[1].replace('\n',''))[0]
            self.message_post(body='Kết quả trạng thái hóa đơn.<br/> %s' %res_json)
            state_selection = dict(self._fields['state'].selection)
            if res_json.get('ma','') and res_json.get('ma','') in state_selection:
                self.write({'state': res_json.get('ma','')})
                if res_json.get('ma','') == 'CM':
                    self.action_update_vat_product_quantity()
        else:
            self.message_post(body='Xảy ra lỗi khi cập nhật trạng thái hóa đơn.<br/> %s' %result[1])
