# -*- coding: utf-8 -*-

from asyncore import write
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from urllib.parse import urlencode
from datetime import datetime
import base64

import random
import string
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


def xml2json_from_elementtree(el, preserve_whitespaces=False):
    """ xml2json-direct
    Simple and straightforward XML-to-JSON converter in Python
    New BSD Licensed
    http://code.google.com/p/xml2json-direct/
    """
    res = {}
    if el.tag[0] == "{":
        ns, name = el.tag.rsplit("}", 1)
        res["tag"] = name
        res["namespace"] = ns[1:]
    else:
        res["tag"] = el.tag
    res["attrs"] = {}
    for k, v in el.items():
        res["attrs"][k] = v
    kids = []
    if el.text and (preserve_whitespaces or el.text.strip() != ''):
        kids.append(el.text)
    for kid in el:
        kids.append(xml2json_from_elementtree(kid, preserve_whitespaces))
        if kid.tail and (preserve_whitespaces or kid.tail.strip() != ''):
            kids.append(kid.tail)
    res["children"] = kids
    return res


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

    def generateFkey(self, length=13):
        chars = string.ascii_letters + string.digits
        while True:
            fkey = ''.join(random.choices(chars, k=length))
            if not self.search_count([('vh_einv_fkey', '=', fkey)]):
                return fkey

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
    partner_id = fields.Many2one('res.partner', 'VH E-Invoice Contact', tracking=True)
    # Customer Information
    customer_name = fields.Char('Contact Name', related='partner_id.name', store=True)
    customer_code = fields.Char('Customer Code', related='partner_id.ref', store=True)
    customer_vat = fields.Char('VAT', related='partner_id.vat', store=True, tracking=True)
    customer_address = fields.Char('VAT Address', related='partner_id.vi_full_address', store=True)
    customer_email = fields.Char('Customer Emails', related='partner_id.email', tracking=True)
    is_individual_customer = fields.Boolean(related='partner_id.is_company', store=True)
    tax_id = fields.Many2one('account.tax', string='VAT', compute='_compute_vat', store=True, tracking=True)
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
    buyer_responsible = fields.Many2one('res.partner', string='Buyer Responsible')
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
        for rec in self:
            if rec.state != 'N' and not self.env.user.has_group('base.group_system'):
                raise UserError(_('You can not delete the invoice not in draft state!'))
            # if rec.state not in ['N','XN']:
            #     raise UserError(_('Invoice status is not allowed to delete!'))
        return super(VinhHyEInvoice, self).unlink()

    @api.onchange('user_id')
    def onchange_user_id(self):
        for rec in self:
            if rec.user_id:
                rec.team_id = self.env['crm.team'].with_context(default_team_id=rec.team_id.id)._get_default_team_id(user_id=rec.user_id.id)

    @api.depends('line_ids', 'line_ids.price_subtotal', 'line_ids.price_tax', 'line_ids.price_discount' )
    def _compute_amount(self):
        for rec in self:
            rec.amount_untaxed = round(sum(line.price_subtotal for line in rec.line_ids), 0)
            rec.amount_tax = round(sum(line.price_tax for line in rec.line_ids), 0)
            rec.amount_total = rec.amount_untaxed + rec.amount_tax
            rec.amount_discount = round(sum(line.price_discount for line in rec.line_ids), 0)

    @api.depends('line_ids.tax_id')
    def _compute_vat(self):
        for rec in self:
            if rec.line_ids:
                rec.tax_id = rec.line_ids[0].tax_id
            else:
                rec.tax_id = False

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        for rec in self:
            if not rec.fiscal_position_id:
                if rec.partner_id:
                    rec.fiscal_position_id = rec.partner_id.property_account_position_id
    
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
                'Ma_hang': line.product_id.default_code,
                'Ten_hang': line.product_id.name,
                'Dvt': line.uom_id.name,
                'So_luong': line.quantity,
                'Gia': line.price_unit,
                'Tien': line.price_subtotal_signed,
                'Thue_suat': int(line.tax_id.amount),
                'Thue': line.price_tax,
                'Ty_le_chiet_khau': line.discount,
                'chiet_khau': line.price_discount,
                'km':'',
                'so_lo':'',
                'han_dung':''
            })
        return val
    
    def _prepare_company_info(self):
        company = self.partner_id
        return {
            'Mst': company.vat or '',
            'Ten_cty': company.name or '',
            'Dia_chi': company.street or '',
            'Email': company.email or '',
            'Tel': company.phone or company.mobile or '',
        }
    
    def _prepare_customer_info(self):
        return {
            'Nguoi_mua_hang': self.customer_name or '',
        }
    
    def _prepare_value(self):
        return {
            'Ngay_hd': self.date_invoice.strftime("%Y-%m-%d") if self.date_invoice else fields.Date.today().strftime("%Y-%m-%d"),
            'Ky_hieu_mau': self.template_code,
            'So_seri': self.invoice_series,
            'So_hd': str(self.invoice_no),
            **self._prepare_company_info(),
            'so_tk':'',
            **self._prepare_customer_info(),
            'hinh_thuc_thanh_toan': PAYMENT_METHOD.get(self.payment_method, ''),
            'Ma_tte': self.currency_id.name or '',
            'Ty_gia': self.currency_id.inverse_rate or 0,
        }

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
        val.update(**self._prepare_value())
        return val

    # send origin inv
    def action_send_to_issue_vh_einv(self):
        if self.einv_type == 'origin':
            return self.action_send_orgin_vh_einv()

    def action_send_orgin_vh_einv(self):
        if not self.company_id or not self.company_id.vinhhy_einv_username or not self.company_id.vinhhy_einv_password:
            raise UserError(_("Please input Vinh Hy E-Invoice account!"))
        einv_data = self._prepare_einv_data()
        lines_val = self._prepare_inv_line_val()
        data = {
            'user': self.company_id.vinhhy_einv_username,
            'pwd': self.company_id.vinhhy_einv_password,
            'data': {
                'Chitiet': lines_val,
                **einv_data
            }
        }
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
        view = self.env.ref('vinhhy_einvoice.vinhhy_einvoice_form')
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
        else:
            self.message_post(body='Xảy ra lỗi khi cập nhật trạng thái hóa đơn.<br/> %s' %result[1])
