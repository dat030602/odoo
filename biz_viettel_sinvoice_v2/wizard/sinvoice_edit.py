# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import requests
from odoo.exceptions import UserError, AccessError
import json
from datetime import datetime
import uuid
from odoo.addons import decimal_precision as dp
from odoo.tools import email_re, email_split, email_escape_char, float_is_zero, float_compare
_select_edit_type = [
        ("info", "Modify information"),
        ("amount", "Money adjustment"),
        ("replace", "Create replacement invoice"),
    ]
_select_IdType = [
        ('1','ID card'),
        ('2','Business license'),
        ('3','Passport'),
    ]
class SinvoiceEdit(models.TransientModel):
    _name = "sinvoice.edit"
    _description = "Sinvoice edit"
    
    sinvoice_edit_type = fields.Selection(_select_edit_type, "Type", default="info")
    sinvoice_id = fields.Many2one('viettel.sinvoice')
    sinvoice_line_id = fields.Many2one('viettel.sinvoice.line')
    partner_vat_id = fields.Many2one('res.partner')
    invoiceSignedDate = fields.Date('Invoice Signed Date')
    additionalReferenceDesc = fields.Char('Additional Reference Desc')
    additionalReferenceDate = fields.Date('Additional Reference Date')
    invoiceIssuedDate = fields.Datetime('Invoice Issued Date')#Thời gian phát hành
    buyerPhoneNumber = fields.Char("Buyer phone number")
    buyerName = fields.Char("Buyer name")
    buyerCode = fields.Char("Buyer code")
    buyerTaxCode = fields.Char("Buyer tax code")
    buyerEmail = fields.Char("Buyer email")
    buyerIdType = fields.Selection(_select_IdType,'Buyer IdType')
    buyerIdNo = fields.Char("Buyer Id .No")
    buyerLegalName = fields.Char("Buyer legal name")
    buyerAddressLine = fields.Char("Buyer address line")
    
    new_buyerPhoneNumber = fields.Char("Buyer phone number")
    new_buyerName = fields.Char("Buyer name")
    new_buyerCode = fields.Char("Buyer code")
    new_buyerTaxCode = fields.Char("Buyer tax code")
    new_buyerEmail = fields.Char("Buyer email")
    new_buyerIdType = fields.Selection(_select_IdType,'Buyer IdType')
    new_buyerIdNo = fields.Char("Buyer Id .No")
    new_buyerLegalName = fields.Char("Buyer legal name")
    new_buyerAddressLine = fields.Char("Buyer address line")
    vsi_template = fields.Char("Template")
    vsi_series = fields.Char("vsi_series")
    originalInvoiceId = fields.Char("originalInvoiceId")
    company_id = fields.Many2one('res.company', string='Company', )
    sinvoice_data_ids = fields.One2many('viettel.sinvoice.data.edit', 'sinvoice_edit_id', string='Invoice Datas',)
    type = fields.Selection([
            ('out_invoice', 'Customer Invoice'),
            ('in_invoice', 'Vendor Bill'),
            ('out_refund', 'Customer Credit Note'),
            ('in_refund', 'Vendor Credit Note'),
        ])
    journal_id = fields.Many2one('account.journal', string='Journal',)
    company_type = fields.Selection(related='partner_vat_id.company_type')

    @api.model
    def default_get(self, fields):
        
        rec = super(SinvoiceEdit, self).default_get(fields)
        invoice_edit = self._context.get('active_id')
        account_invoice_line = self.env['viettel.sinvoice.line']
        sinvoice_line_id = account_invoice_line.browse(invoice_edit)
        sinvoice_id = sinvoice_line_id.sinvoice_id
        partner_vat_id = sinvoice_id.partner_vat_id
        sinvoice_data_ids = []
        for sinvoice_data_id in sinvoice_id.sinvoice_data_ids:
            # sinvoice_data_ids.append({
            #     'product_id': sinvoice_data_id.product_id.id,
            #     'name': sinvoice_data_id.name,
            #     'product_uom_id': sinvoice_data_id.product_uom_id.id,
            #     'quantity': sinvoice_data_id.quantity,
            #     'price_unit': sinvoice_data_id.price_unit,
            #     'tax_ids': [(6, 0, sinvoice_data_id.tax_ids.ids)],
            #     'price_total': sinvoice_data_id.price_subtotal,
            # })
            line_data = {
                'product_id': sinvoice_data_id.product_id.id,
                'name': sinvoice_data_id.name,
                'product_uom_id': sinvoice_data_id.product_uom_id.id,
                'quantity': sinvoice_data_id.quantity,
                'price_unit': sinvoice_data_id.price_unit,
                'tax_ids': [(6, 0, sinvoice_data_id.tax_ids.ids)],
                'price_total': sinvoice_data_id.price_subtotal,
                'vsi_item_type': sinvoice_data_id.vsi_item_type,
            }
            if sinvoice_data_id.display_type:
                line_data['display_type'] = sinvoice_data_id.display_type
            sinvoice_data_ids.append(line_data)
        rec.update({
            'sinvoice_id': sinvoice_id.id,
            'partner_vat_id': partner_vat_id.id,
            'buyerName': sinvoice_id.partner_vat_name,
            'buyerCode': partner_vat_id.ref,
            'buyerTaxCode': sinvoice_id.partner_vat,
            'buyerLegalName': partner_vat_id.name,
            'buyerAddressLine': sinvoice_id.partner_vat_address,
            'buyerIdType': partner_vat_id.id_type,
            'buyerIdNo': partner_vat_id.identity_card,
            'new_buyerName': sinvoice_id.partner_vat_name,
            'new_buyerCode': partner_vat_id.ref,
            'new_buyerTaxCode': sinvoice_id.partner_vat,
            'new_buyerLegalName': partner_vat_id.name,
            'new_buyerAddressLine': sinvoice_id.partner_vat_address,
            'new_buyerIdType': partner_vat_id.id_type,
            'new_buyerIdNo': partner_vat_id.identity_card,
            'invoiceIssuedDate': sinvoice_id.invoiceIssuedDate,
            'originalInvoiceId': sinvoice_line_id.invoiceNo,
            'vsi_series': sinvoice_id.config_id.vsi_series,
            'vsi_template': sinvoice_id.config_id.vsi_template,
            'sinvoice_data_ids': [(0,0, line_id) for line_id in sinvoice_data_ids],
            'company_id': sinvoice_id.company_id.id,
            'type': sinvoice_id.type,
            'journal_id': sinvoice_id.journal_id.id,
            'sinvoice_line_id': sinvoice_line_id.id,
        })
        return rec 
    
    
    def do_edit(self, draft=False):
        if self.invoiceIssuedDate:
            buyer_info = {
                "email": self.new_buyerEmail or self.buyerEmail,
                "street": self.new_buyerAddressLine or self.buyerAddressLine,
                'phone': self.new_buyerPhoneNumber or self.buyerPhoneNumber,
                'ref': self.new_buyerCode or self.buyerCode,
                'vat': self.new_buyerTaxCode or self.buyerTaxCode,
                'id_type': self.new_buyerIdType or self.buyerIdType,
                'identity_card': self.new_buyerIdNo or self.buyerIdNo,
            }
            if self.new_buyerName:
                buyer_info['name'] = self.new_buyerName

            # if self.partner_vat_id:
            #     self.partner_vat_id.write(buyer_info)
            sinvoice_id = self.sinvoice_id
            sinvoice_line_new = self.create_invoice_vninvoice(sinvoice_id, draft)
            if not draft:
                if self.sinvoice_edit_type == 'amount':
                    self.create_odoo_invoice_adjust(sinvoice_id, sinvoice_line_new)
                if self.sinvoice_edit_type == 'replace':
                    self.create_odoo_invoice_replace(sinvoice_id, sinvoice_line_new)
            else:
                if not sinvoice_line_new:
                    raise UserError(_("You don't have any new changes."))
                return {
                    'name': _("Preview"),
                    'type': 'ir.actions.act_url',
                    'url': 'web/content/%s' % sinvoice_line_new.id,
                    'target': 'new',
                }

        return {
            "name": "Viettel Sinvoice",
            "type": "ir.actions.act_window",
            "res_model": "viettel.sinvoice",
            "res_id": sinvoice_id.id,
            "views": [(False, "form")],
        }

    def create_odoo_invoice_replace(self, sinvoice_id, sinvoice_line_new):
        config_id = sinvoice_id.config_id
        if not config_id or not config_id.allow_create_odoo_inv_adjust:
            return
            
        invoice_id = sinvoice_id.invoice_id
        lines = self.sinvoice_data_ids
        if invoice_id:
            vals = invoice_id.with_context(active_test=False).copy_data({
                    'invoice_line_ids': [],
                    'line_ids': []
            })[0]
            vals.update({
                'move_type': 'out_invoice',
                'state': 'draft',
                'sinvoice_adjust_id': sinvoice_id.id,
                'sinvoice_line_adjust_id':sinvoice_line_new and sinvoice_line_new.id,
                'invoice_line_ids':[(0,0, {
                    'display_type': 'product',
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'tax_ids': [(6,0, line.tax_ids.ids)],
                    'discount': line.discount
                }) for line in lines]
            })
            invoice_id.button_cancel()
        else:
            vals = {
                'partner_id': sinvoice_id.partner_vat_id.id,
                'journal_id': sinvoice_id.journal_id.id,
                'sinvoice_line_adjust_id':sinvoice_line_new and sinvoice_line_new.id,
                'sinvoice_adjust_id': sinvoice_id.id,
                'move_type': 'out_invoice',
                'state': 'draft',
                'invoice_line_ids': [(0,0, {
                    'display_type': 'product',
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'tax_ids': [(6,0, line.tax_ids.ids)],
                    'discount': line.discount
                }) for line in lines]
            }

        new_inv = self.env['account.move'].create(vals)
        
    def create_invoice_vninvoice(self, sinvoice_id, draft=False):
        result = False
        invoiceIssuedDate = datetime.now()
        invoiceIssuedDate_int= int(datetime.strptime(str(invoiceIssuedDate.strftime("%Y-%m-%d %H:%M:%S")), "%Y-%m-%d %H:%M:%S").timestamp())# new
        originalInvoiceIssueDate = int(datetime.strptime(str(self.invoiceIssuedDate.strftime("%Y-%m-%d %H:%M:%S")), "%Y-%m-%d %H:%M:%S").timestamp())
        invoiceSignedDate = self.invoiceSignedDate and int(datetime.strptime(str(self.invoiceSignedDate.strftime("%Y-%m-%d %H:%M:%S")), "%Y-%m-%d %H:%M:%S").timestamp()) or False
        additionalReferenceDate = self.additionalReferenceDate and int(datetime.strptime(str(self.additionalReferenceDate.strftime("%Y-%m-%d %H:%M:%S")), "%Y-%m-%d %H:%M:%S").timestamp()) or False
        adjustmentInvoiceType = 0
        adjustmentType = 0
        if self.sinvoice_edit_type == 'info':
            adjustmentType= 5
            adjustmentInvoiceType= 2
        if self.sinvoice_edit_type == 'amount':
            adjustmentType= 5
            adjustmentInvoiceType= 1
        if self.sinvoice_edit_type == 'replace':
            adjustmentType= 3
        
        generalInvoiceInfo = {
            "transactionUuid": "%s"%( uuid.uuid1()),
            "userName": sinvoice_id.user_id.name,
            "currencyCode": sinvoice_id.currency_id.name,
            "invoiceIssuedDate": invoiceIssuedDate_int * 1000,
            "templateCode": sinvoice_id.config_id.vsi_template,  # config
            "invoiceSeries": sinvoice_id.config_id.vsi_series,  # config
            "invoiceType": sinvoice_id.config_id.vsi_type.code,  # config
            "paymentType": "TM/CK",
            "paymentTypeName": "TM/CK",
            "paymentStatus": True,
            "invoiceSignedDate": invoiceSignedDate * 1000,
            "originalInvoiceId": sinvoice_id.name,
            "originalInvoiceIssueDate": originalInvoiceIssueDate * 1000,#Ngày phát hành của hóa đơn gốc
            "additionalReferenceDesc": self.additionalReferenceDesc,
            "additionalReferenceDate": additionalReferenceDate * 1000, #Ngày thỏa thuận
            "adjustmentType": adjustmentType,
        }
        if adjustmentInvoiceType:
            generalInvoiceInfo["adjustmentInvoiceType"] =  adjustmentInvoiceType
            
        payments = [{
            "paymentMethodName": "TM/CK",
        }]
        buyerInfo = {
            "buyerAddressLine": self.new_buyerAddressLine or self.buyerAddressLine,
            'buyerCode': self.new_buyerCode or self.buyerCode,
            'buyerName': self.new_buyerName or self.buyerName or ''
        }
        if self.new_buyerTaxCode or self.buyerTaxCode:
            buyerInfo['buyerTaxCode'] = self.new_buyerTaxCode or self.buyerTaxCode

        if self.new_buyerLegalName or self.buyerLegalName:
            buyerInfo.update({'buyerLegalName': self.new_buyerLegalName or self.buyerLegalName})

        if self.new_buyerIdType or self.buyerIdType:
            buyerInfo['buyerIdType'] = self.new_buyerIdType or self.buyerIdType

        if self.new_buyerIdNo or self.buyerIdNo:
            buyerInfo['buyerIdNo'] = self.new_buyerIdNo or self.buyerIdNo
        
        breakdown = {}
        taxAmount = 0
        totalAmountWithoutTax = 0
        totalAmountWithTax = 0
        for invoice_line in sinvoice_id.sinvoice_data_ids:
            item_type = invoice_line.vsi_item_type or sinvoice_id._get_default_item_type_for_line(invoice_line)
            is_discount = (item_type == 'chiet_khau')
            
            if self.sinvoice_edit_type == 'amount':
                if is_discount:
                    line_sign = -1 if invoice_line.edit_type == 'increase' else 1
                else:
                    line_sign = 1 if invoice_line.edit_type == 'increase' else -1
            else:
                line_sign = -1 if is_discount else 1
                
            if (self.sinvoice_edit_type == 'amount' and invoice_line.edit_type in ["increase", "reduction"]) or self.sinvoice_edit_type == 'replace':
                taxAmount += sinvoice_id.currency_id.round(line_sign * (invoice_line.price_total - invoice_line.price_subtotal))
                totalAmountWithoutTax += sinvoice_id.currency_id.round(line_sign * invoice_line.price_subtotal)
                totalAmountWithTax += sinvoice_id.currency_id.round(line_sign * invoice_line.price_total)
            if self.sinvoice_edit_type != 'info':
                if len(invoice_line.tax_ids):
                    for tax_id in invoice_line.tax_ids:
                        if tax_id.id not in breakdown:
                            if tax_id.not_taxable:
                                taxPercentage = -2
                            elif tax_id.not_declared_paid:
                                taxPercentage = -1
                            else:
                                taxPercentage = tax_id.amount
                            sinvoice_id = self.sinvoice_id
                            breakdown[tax_id.id] = {
                                "taxPercentage": taxPercentage,
                                "taxableAmount": sinvoice_id.currency_id.round(line_sign * invoice_line.price_subtotal),
                                "taxAmount": sinvoice_id.currency_id.round(line_sign * invoice_line.price_subtotal * tax_id.amount / 100),
                            }
                        else:
                            breakdown[tax_id.id]["taxableAmount"] += sinvoice_id.currency_id.round(line_sign * invoice_line.price_subtotal)
                            breakdown[tax_id.id]["taxAmount"] += sinvoice_id.currency_id.round(line_sign * invoice_line.price_subtotal * tax_id.amount / 100)
                        break
        taxBreakdowns = []
        for bd in breakdown:
            breakdown[bd]["taxableAmount"] = abs(breakdown[bd]["taxableAmount"])
            breakdown[bd]["taxAmount"] = abs(breakdown[bd]["taxAmount"])
            taxBreakdowns.append(breakdown[bd])
        invoiceDetails = self.get_itemInfo(sinvoice_id)
        if invoiceDetails:
            summarizeInfo = sinvoice_id.get_summarize_info(invoiceDetails)
            if self.sinvoice_edit_type == 'amount':
                summarizeInfo.update({
                    "isTotalAmountPos": True,
                    "isTotalTaxAmountPos": True,
                    "isTotalAmtWithoutTaxPos": True,
                    "isDiscountAmtPos": True
                })
            data = {
                "itemInfo": invoiceDetails,
                "generalInvoiceInfo": generalInvoiceInfo,
                "buyerInfo": buyerInfo,
                "summarizeInfo": summarizeInfo,
                "taxBreakdowns": taxBreakdowns,
                "payments": payments,
            }
            result = self.sinvoice_line_id.edit_invoice_info(data, self.get_edit_type_name(self.sinvoice_edit_type), self.sinvoice_edit_type, draft)
            if not draft:
                result.write({
                    'invoiceIssuedDate':invoiceIssuedDate,
                    'originalInvoiceIssueDate': self.invoiceIssuedDate
                })

        return result

    def do_edit_preview(self):
        return self.do_edit(True)
    
    def get_itemInfo(self, sinvoice_id):
        invoiceDetails = []
        templateCode = sinvoice_id.config_id.vsi_template
        invoiceSeries = sinvoice_id.config_id.vsi_series
        invoiceIssuedDate = datetime.now().strftime("%Y-%m-%d") # new
        sinvoice_data_obj = self.env['viettel.sinvoice.data']
        if self.sinvoice_edit_type == 'info':
            note = _("Điều chỉnh thông tin khách hàng cho hóa đơn điện tử mẫu %s ký hiệu %s số %s lập ngày %s:")%(templateCode, invoiceSeries, sinvoice_id.name, invoiceIssuedDate)
            note_info = []
            #if self.buyerPhoneNumber != self.new_buyerPhoneNumber:
            #    note_info.append('Phone: %s-->%s'%(self.buyerPhoneNumber or '', self.new_buyerPhoneNumber or ''))
            if self.buyerCode != self.new_buyerCode:
                note_info.append(_('Mã khách hàng:%s-->%s')%(self.buyerCode or '', self.new_buyerCode or ''))
            if self.buyerName != self.new_buyerName:
                note_info.append(_('Tên người mua:%s-->%s')%(self.buyerName or '', self.new_buyerName or ''))
            if self.buyerTaxCode != self.new_buyerTaxCode:
                note_info.append(_('Mã số thuế:%s-->%s')%(self.buyerTaxCode or '', self.new_buyerTaxCode or ''))
            if self.buyerEmail != self.new_buyerEmail:
                note_info.append(_('Địa chỉ Email: %s-->%s')%(self.buyerEmail or '', self.new_buyerEmail or ''))
            if self.buyerIdType != self.new_buyerIdType:
                buyerIdType = self.get_buyerIdType_name(self.buyerIdType)
                new_buyerIdType = self.get_buyerIdType_name(self.new_buyerIdType)
                note_info.append(_('Loại giấy tờ: %s-->%s')%(buyerIdType or '', new_buyerIdType or ''))
            if self.buyerIdNo != self.new_buyerIdNo:
                note_info.append(_('Số giấy tờ: %s-->%s')%(self.buyerIdNo or '', self.new_buyerIdNo or ''))
            if self.buyerLegalName != self.new_buyerLegalName:
                note_info.append(_('Tên đơn vị: %s-->%s')%(self.buyerLegalName or '', self.new_buyerLegalName or ''))
            if self.buyerAddressLine != self.new_buyerAddressLine:
                note_info.append(_('Địa chỉ: %s-->%s')%(self.buyerAddressLine or '', self.new_buyerAddressLine or ''))
            if len(note_info) > 0 :
                note = "%s %s" %(note, '; '.join(note_info))
                line_data = {
                    "adjustmentTaxAmount": 1,
                    "selection": 2,
                    "itemName": note,
                }
                invoiceDetails.append(line_data)
            else:
                invoiceDetails = False
        elif self.sinvoice_edit_type == 'amount':
            sinvoice_id.sinvoice_data_ids.unlink()
            for line in self.sinvoice_data_ids:
                vals = sinvoice_id.create_data_sinvoice_line(line, self.sinvoice_edit_type, line.edit_type)
                for val in vals:
                    val['vsi_item_type'] = line.vsi_item_type
                    sinvoice_data_obj.create(val)

            invoiceDetails = sinvoice_id.get_invoice_details(self.sinvoice_edit_type, invoiceIssuedDate)
            if invoiceDetails:
                discount_lines_info = {}
                for line in sinvoice_id.sinvoice_data_ids:
                    item_type = line.vsi_item_type or sinvoice_id._get_default_item_type_for_line(line)
                    if item_type == 'chiet_khau':
                        discount_lines_info["product_" + str(line.product_id.id)] = line.edit_type
                
                for detail in invoiceDetails:
                    item_code = detail.get('itemCode')
                    if item_code in discount_lines_info:
                        edit_type = discount_lines_info[item_code]
                        if edit_type == 'reduction':
                            detail['isIncreaseItem'] = True
                            detail['quantity'] = abs(detail.get('quantity', 0))
                            detail['unitPrice'] = abs(detail.get('unitPrice', 0))
                            detail['itemTotalAmountWithoutTax'] = abs(detail.get('itemTotalAmountWithoutTax', 0))
                            detail['itemTotalAmountWithTax'] = abs(detail.get('itemTotalAmountWithTax', 0))
                            detail['itemTotalAmountAfterDiscount'] = abs(detail.get('itemTotalAmountAfterDiscount', 0))
                            if 'taxAmount' in detail:
                                detail['taxAmount'] = abs(detail.get('taxAmount', 0))
                        elif edit_type == 'increase':
                            detail['isIncreaseItem'] = False
                            detail['quantity'] = -abs(detail.get('quantity', 0))
                            detail['unitPrice'] = -abs(detail.get('unitPrice', 0))
                            detail['itemTotalAmountWithoutTax'] = -abs(detail.get('itemTotalAmountWithoutTax', 0))
                            detail['itemTotalAmountWithTax'] = -abs(detail.get('itemTotalAmountWithTax', 0))
                            detail['itemTotalAmountAfterDiscount'] = -abs(detail.get('itemTotalAmountAfterDiscount', 0))
                            if 'taxAmount' in detail:
                                detail['taxAmount'] = -abs(detail.get('taxAmount', 0))
        elif self.sinvoice_edit_type == 'replace':
            sinvoice_id.sinvoice_data_ids.unlink()
            for line in self.sinvoice_data_ids:
                vals = sinvoice_id.create_data_sinvoice_line(line)
                print("vals", vals)
                for val in vals:
                    sinvoice_data_obj.create(val)
            invoiceDetails = sinvoice_id.get_invoice_details(self.sinvoice_edit_type, invoiceIssuedDate)
        return invoiceDetails
    
    def get_buyerIdType_name(self, buyerIdType):
        result = ''
        if buyerIdType == 1:
            result = _('ID card')
        if buyerIdType == 2:
            result = _('Business license')
        if buyerIdType == 3:
            result = _('Passport')
        return result
    
    def get_edit_type_name(self, type):
        for edit_type in _select_edit_type:
            if edit_type[0] == type:
                return edit_type[1]

    def create_odoo_invoice_adjust(self, sinvoice_id, sinvoice_line_new):
        config_id = sinvoice_id.config_id
        if not config_id or not config_id.allow_create_odoo_inv_adjust:
            return

        if self.sinvoice_edit_type != 'amount':
            return

        group_type = {}
        for line in self.sinvoice_data_ids:
            if not line.edit_type:
                continue

            if line.edit_type not in group_type:
                group_type[line.edit_type] = [line]
            else:
                group_type[line.edit_type].append(line)

        for key, lines in group_type.items():
            invoice_id = sinvoice_id.invoice_id
            move_type = False
            if key == 'increase':
                move_type = 'out_invoice'

            if key == 'reduction':
                move_type = 'out_refund'

            if invoice_id:
                vals = invoice_id.with_context(active_test=False).copy_data({
                        'invoice_line_ids': [],
                        'line_ids': []
                })[0]
                vals.update({
                    'move_type': move_type,
                    'state': 'draft',
                    'sinvoice_adjust_id': sinvoice_id.id,
                    'sinvoice_line_adjust_id':sinvoice_line_new and sinvoice_line_new.id,
                    'invoice_line_ids':[(0,0, {
                        'display_type': 'product',
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
                        'tax_ids': [(6,0, line.tax_ids.ids)],
                        'discount': line.discount
                    }) for line in lines]
                })
            else:
                vals = {
                    'partner_id': sinvoice_id.partner_vat_id.id,
                    'journal_id': sinvoice_id.journal_id.id,
                    'sinvoice_line_adjust_id':sinvoice_line_new and sinvoice_line_new.id,
                    'sinvoice_adjust_id': sinvoice_id.id,
                    'move_type': move_type,
                    'state': 'draft',
                    'invoice_line_ids': [(0,0, {
                        'display_type': 'product',
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
                        'tax_ids': [(6,0, line.tax_ids.ids)],
                        'discount': line.discount
                    }) for line in lines]
                }

            new_inv = self.env['account.move'].create(vals)

class AccountInvoiceDataEdit(models.TransientModel):
    _name = 'viettel.sinvoice.data.edit'
    _description = 'Viettel sinvoice data edit'
    
    @api.depends('price_unit', 'discount', 'tax_ids', 'quantity',
        'product_id', 'sinvoice_id.partner_vat_id', 'sinvoice_id.currency_id', 'sinvoice_id.company_id',
        'sinvoice_id.date_invoice', 'sinvoice_id.date')
    def _compute_price(self):
        for res in self:
            currency = res.sinvoice_id and res.sinvoice_id.currency_id or None
            price = res.price_unit * (1 - (res.discount or 0.0) / 100.0)
            taxes = False
            if res.tax_ids:
                taxes = res.tax_ids.compute_all(price, currency, res.quantity, product=res.product_id, partner=res.sinvoice_id.partner_vat_id)
            res.tax_total = taxes['total_included'] - taxes['total_excluded'] if taxes else res.quantity * price
            res.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else res.quantity * price
            res.price_total = taxes['total_included'] if taxes else res.price_subtotal
            if res.sinvoice_id.currency_id and res.sinvoice_id.currency_id != res.sinvoice_id.company_id.currency_id:
                currency = res.sinvoice_id.currency_id
                date = res.sinvoice_id.date
                price_subtotal_signed = currency._convert(price_subtotal_signed, res.sinvoice_id.company_id.currency_id, res.company_id or res.env.user.company_id, date or fields.Date.today())
            sign = res.sinvoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
            res.price_subtotal_signed = price_subtotal_signed * sign
    
    sinvoice_id = fields.Many2one('viettel.sinvoice', string='Invoice Reference', related='sinvoice_edit_id.sinvoice_id',)
    edit_type = fields.Selection([
            ('increase', 'Increase'),
            ('reduction', 'Reduction quantity'),
            ('reduction_price','Reduction price')
        ], string='Edit Type')
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict', index=True)
    name = fields.Text(string='Description')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
        ondelete='set null', index=True)
    quantity = fields.Float(string='Quantity', default=1)
    price_unit = fields.Float(string='Unit Price')
    tax_ids = fields.Many2many('account.tax','account_invoice_data_edit_tax', 'invoice_line_edit_id', 'tax_id',
        string='Taxes', domain=[('type_tax_use','!=','none'), '|', ('active', '=', False), ('active', '=', True)])
    sinvoice_edit_id = fields.Many2one('sinvoice.edit', string='sinvoice edit')
    discount = fields.Float(string='Discount (%)', default=0.0)
    tax_total = fields.Float(string='Taxes Total',
        store=True, readonly=True, compute='_compute_price')
    price_subtotal = fields.Float(string='Amount (without Taxes)',
        store=True, readonly=True, compute='_compute_price', help="Total amount without taxes")
    price_total = fields.Float(string='Amount (with Taxes)',
        store=True, readonly=True, compute='_compute_price', help="Total amount with taxes")
    price_subtotal_signed = fields.Float(string='Amount Signed',
        store=True, readonly=True, compute='_compute_price',
        help="Total amount in the currency of the company, negative for credit note.")
    account_id = fields.Many2one('account.account', string='Account',
        readonly=True, states={'draft': [('readonly', False)]},
        domain=[('deprecated', '=', False)], help="The partner account used for this invoice.")
    company_id = fields.Many2one('res.company', string='Company',
        related='sinvoice_id.company_id', store=True, readonly=True, related_sudo=False)
    currency_id = fields.Many2one('res.currency', related='sinvoice_id.currency_id', store=True, related_sudo=False, readonly=False)
    sinvoice_edit_type = fields.Selection(related='sinvoice_edit_id.sinvoice_edit_type')
    display_type = fields.Selection([
		('line_section', "Section"),
		('line_note', "Note")], default=False)
    vsi_item_type = fields.Selection([
        ('hang_hoa', 'Hàng Hóa'),
        ('ghi_chu', 'Ghi chú'),
        ('chiet_khau', 'Chiết khấu'),
        ('bang_ke', 'Bảng kê'),
        ('phi_khac', 'Phí khác'),
    ], string='Loại mặt hàng', default='hang_hoa')
    sequence = fields.Integer(string="Sequence")
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        if not self.sinvoice_id:
            return
        part = self.sinvoice_id.partner_vat_id
        fpos = self.sinvoice_id.fiscal_position_id
        company = self.sinvoice_id.company_id
        currency = self.sinvoice_id.currency_id
        type = self.sinvoice_id.type
        if not part:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a partner.'),
                }
            return {'warning': warning}
        if not self.product_id:
            if type not in ('in_invoice', 'in_refund'):
                self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            self_lang = self
            if part.lang:
                self_lang = self.with_context(lang=part.lang)
            product = self_lang.product_id
            account = self.get_invoice_line_account(type, product, fpos, company)
            if account:
                self.account_id = account.id
            self._set_taxes()
            product_name = self_lang._get_invoice_line_name_from_product()
            if product_name != None:
                self.name = product_name
            if not self.product_uom_id or product.uom_id.category_id.id != self.product_uom_id.category_id.id:
                self.product_uom_id = product.uom_id.id
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]
            if company and currency:
                if self.product_uom_id and self.product_uom_id.id != product.uom_id.id:
                    self.price_unit = product.uom_id._compute_price(self.price_unit, self.product_uom_id)
            if product.default_code == 'CK.KM26.KX':
                self.vsi_item_type = 'chiet_khau'
            else:
                detailed_type = getattr(product, 'detailed_type', False) or getattr(product, 'type', False)
                if detailed_type in ['product', 'consu', 'service']:
                    self.vsi_item_type = 'hang_hoa'
        return {'domain': domain}

    def get_invoice_line_account(self, type, product, fpos, company):
        accounts = product.product_tmpl_id.get_product_accounts(fpos)
        if type in ('out_invoice', 'out_refund'):
            return accounts['income']
        return accounts['expense']
    
    def _set_taxes(self):
        """ Used in on_change to set taxes and price"""
        self.ensure_one()
        # Keep only taxes of the company
        company_id = self.company_id or self.env.user.company_id
        if self.sinvoice_id.type in ('out_invoice', 'out_refund'):
            taxes = self.product_id.taxes_id.filtered(lambda r: r.company_id == company_id) or self.account_id.tax_ids or self.sinvoice_id.company_id.account_sale_tax_id
        else:
            taxes = self.product_id.supplier_taxes_id.filtered(lambda r: r.company_id == company_id) or self.account_id.tax_ids or self.sinvoice_id.company_id.account_purchase_tax_id
        self.tax_ids = fp_taxes = self.sinvoice_id.fiscal_position_id.map_tax(taxes)
        fix_price = self.env['account.tax']._fix_tax_included_price
        if self.sinvoice_id.type in ('in_invoice', 'in_refund'):
            prec = self.env['decimal.precision'].precision_get('Product Price')
            if not self.price_unit or float_compare(self.price_unit, self.product_id.standard_price, precision_digits=prec) == 0:
                self.price_unit = fix_price(self.product_id.standard_price, taxes, fp_taxes)
                self._set_currency()
        else:
            self.price_unit = fix_price(self.product_id.lst_price, taxes, fp_taxes)
            self._set_currency()
    
    def _set_currency(self):
        company = self.sinvoice_id.company_id
        currency = self.sinvoice_id.currency_id
        if company and currency:
            if company.currency_id != currency:
                self.price_unit = self.price_unit * currency.with_context(dict(self._context or {}, date=self.sinvoice_id.date_invoice)).rate
                
    def _get_invoice_line_name_from_product(self):
        """ Returns the automatic name to give to the invoice line depending on
        the product it is linked to.
        """
        self.ensure_one()
        if not self.product_id:
            return ''
        invoice_type = self.sinvoice_id.type
        rslt = self.product_id.partner_ref
        if invoice_type in ('in_invoice', 'in_refund'):
            if self.product_id.description_purchase:
                rslt += '\n' + self.product_id.description_purchase
        else:
            if self.product_id.description_sale:
                rslt += '\n' + self.product_id.description_sale
        return rslt