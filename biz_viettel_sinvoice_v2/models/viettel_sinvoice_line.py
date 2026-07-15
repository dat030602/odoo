# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api,_
import json
from odoo.exceptions import UserError, AccessError
import base64
import logging
_logger = logging.getLogger(__name__)
import time
from odoo.tools.misc import clean_context
from dateutil.relativedelta import relativedelta


class AccountSinvoiceLine(models.Model):
    _name = "viettel.sinvoice.line"
    _description = "Viettel S-Invoice Line"
    
    name = fields.Char('Name')
    type = fields.Selection([
        ('original', 'Invoice Original'),#Hóa đơn gốc
        ("adjusted", "Invoice adjusted"),#Hóa đơn điều chỉnh
        ("replace", "Invoice replace"),#Hóa đơn thay thế
        ("canceled", 'Invoice canceled'),#Hóa đơn xóa bỏ
        ("adjusted_money", 'Invoice adjusted money'),#Hóa đơn xóa bỏ
    ], string='Hình thức hóa đơn', default='original')
    transactionID = fields.Char('Transaction ID')
    transactionUuid = fields.Char("Transaction Uuid", copy=False)
    supplierTaxCode = fields.Char("Supplier Tax Code")
    
    reservationCode = fields.Char("Reservation Code")
    sinvoice_id = fields.Many2one("viettel.sinvoice", "Sinvoice")
    state = fields.Selection([
        ('draft', 'Invoice Draft'),
        ('created', 'Created'),
        ('canceled', 'Invoice Canceled'),
        ('info', 'Modified information'),
        ('amount', 'Money adjusted'),
        ('replace', 'Invoice is replaced'),
    ], string='S-Invoice status', copy=False, default="draft")
    invoiceIssuedDate = fields.Datetime('Invoice Issued Date')#Thời gian phát hành
    originalInvoiceIssueDate = fields.Datetime('Original Invoice Issue Date')#Thời gian phát hành hóa đơn gốc
#     sinvoice_lookup_id = fields.Many2one("viettel.sinvoice.lookups")
    invoiceId = fields.Char()
    invoiceType = fields.Many2one('viettel.sinvoice.type', 'Type') #Mã loại hóa đơn
    adjustmentType = fields.Integer("Adjustment Type")
    templateCode = fields.Char("Template Code")
    invoiceSeri = fields.Char("Invoice Seri")
    invoiceNumber = fields.Char("Invoice Number")
    invoiceNo = fields.Char("Invoice No")
    currencyCode = fields.Char("Currency Code")
    total = fields.Float('Total')
#     issueDate = fields.Datetime("issueDate")
    vsi_status = fields.Char("State")
    totalBeforeTax = fields.Float("Total before Tax")
    taxAmount = fields.Float("Tax Amount")
    description = fields.Char("Description")
    buyerName = fields.Char("Buyer Name")
    buyerLegalName = fields.Char("Buyer legal name")
    buyerAddressLine = fields.Char("Buyer address line")
    buyerTaxCode = fields.Char("Buyer Tax Code")
    buyerCode = fields.Char("Buyer Code")
    paymentStatus = fields.Boolean("Payment Status") #Đã thanh toán
    createTime = fields.Datetime("Create Time") 
    contractId = fields.Char("Contract Id")
    contractNo = fields.Char("Contract No")
    taxRate = fields.Char("Tax Rate")
    paymentMethod = fields.Integer("Payment Method")
    paymentTime = fields.Datetime("Payment Time")
    customerId = fields.Char("Customer Id")
    no = fields.Char(".No")
    model = fields.Char(string="Model")
    reference_id = fields.Char(string="Reference")
    attachment_ids = fields.Many2many('ir.attachment', 'sinvoice_line_ir_attachments_rel',
        'sinvoice_line_id', 'attachment_id', string='Attachments')
    sinvoice_pdf = fields.Binary(string='S-Invoice File (PDF)', attachment=True, readonly=True, copy=False, 
        help="The display version of the S-Invoice in PDF format")
    downloaded = fields.Boolean("Downloaded", default=False)
    exchange_file_downloaded = fields.Boolean("Exchange file Downloaded", default=False)
    exchange_file_ids = fields.Many2many('ir.attachment', 'exchange_file_ir_attachments_rel',
        'sinvoice_line_id', 'attachment_id', string='Exchange file')
    vsi_reference_desc = fields.Char(string="vsi_reference_desc")
    vsi_reference_date = fields.Char(string="vsi_reference_date")
    reason = fields.Char(string="Reason cancel")

    def _pepare_do_get_invoice(self):
        with self.pool.cursor() as new_cr:
            self = self.with_env(self.env(cr=new_cr))
            self.sudo()._do_action_get_invoices()
            self.env.cr.commit()

    def _do_action_get_invoices(self):
        try:
            self.action_get_invoices()
        except  Exception as e:
            self.sinvoice_id.message_post(body="Không thể getInvoices %s" % e)
    
    def check_exist(self, invoiceNo = False):
        if invoiceNo:
            invoices = self.search([('invoiceNo','=', invoiceNo)], limit=1)
            return invoices
        return False
    
    
    def action_download_invoice_representation_file(self):
        self.get_invoice_pdf_file()
    
    def action_download_exchange_invoice_file(self):
        self.get_exchange_invoice_file()
    
    def get_data_exchange_invoice_file(self):
        sinvoice_id = self.sinvoice_id
        invoiceIssuedDate_int = int(self.invoiceIssuedDate.timestamp()) * 1000
        data =  {
            'strIssueDate': invoiceIssuedDate_int,
            'supplierTaxCode': sinvoice_id.config_id.vsi_tin,
            'exchangeUser':sinvoice_id.user_id.name,
            'invoiceNo':  self.invoiceNo 
        }
        return data
    
    def get_exchange_invoice_file(self):
        for sinvoice_line in self:
            invoice = sinvoice_line.sinvoice_id
            config_id = invoice.config_id
            api_url = '/services/einvoiceapplication/api/InvoiceAPI/InvoiceWS/createExchangeInvoiceFile'
            data = sinvoice_line.get_data_exchange_invoice_file()
            pdf = False
            file = ''
            headers = { 
                'Content-Type': "application/x-www-form-urlencoded", 
            }
            response = config_id.execute_request(self,"POST", api_url, data=data, headers=headers, urlencoded=True)
            if response.get('success', False):
                data = response['data'] or {}
                fileToBytes = data.get('fileToBytes')
                if fileToBytes:
                    invoiceNo = sinvoice_line.invoiceNo
                    filename = invoiceNo
                    if '.pdf' not in filename:
                        filename = u'%s.pdf'%filename
                    filename= _('Exchange_Invoice_%s')%(filename)

                    attachment = {
                        'name': filename,
                        'datas': fileToBytes,
                        'res_model': self._name,
                        'res_id': self.id,
                        'type': 'binary',
                    }
                    try:
                        attachment_id = self.env['ir.attachment'].create(attachment)
                        if attachment_id and attachment_id.id:
                            sinvoice_line.exchange_file_ids.unlink()
                            sinvoice_line.write({
                                'exchange_file_ids': [(4, attachment_id.id)],
                                'exchange_file_downloaded': True,
                            })
                    except AccessError:
                        _logger.warning("Cannot save PDF report %r as attachment", attachment['name'])
                    else:
                        _logger.warning('The PDF document %s is now saved in the database', attachment['name'])
            else:
                raise UserError("Exchange invoice Errors: (%s)" % (response['error']))
    
    def get_invoice_pdf_file(self, exchange_file = False):
        self = self.with_context(clean_context(self._context))
        for sinvoice_line in self:
            invoice = sinvoice_line.sinvoice_id
            config_id = invoice.config_id
            api_url = '/services/einvoiceapplication/api/InvoiceAPI/InvoiceUtilsWS/getInvoiceRepresentationFile'
            
            body = {
                "supplierTaxCode": config_id.vsi_tin,
                "invoiceNo": self.invoiceNo,
                "templateCode": config_id.vsi_template,
                "fileType": "PDF",
            }
            headers = {
                "Content-type": "application/json; charset=utf-8",
            }

            response = config_id.execute_request(self, 'POST', api_url,  headers=headers, data=body)
            if response.get("success", False):
                data = response['data']
                errorCode = data.get("errorCode")
                description = data.get('description')
                fileToBytes = data.get('fileToBytes')
                if fileToBytes:
                    filename = u'%s.pdf'%self.invoiceNo
                    if fileToBytes:
                        attachment_id = self.env['ir.attachment'].search([('res_model','=',self._name),('res_id','=',self.id),('name','=',filename)],limit=1)
                        if not attachment_id:
                            attachment = {
                                'name': filename,
                                'datas': fileToBytes,
                                'res_model': self._name,
                                'res_id': self.id,
                            }
                            attachment_id = self.env['ir.attachment'].create(attachment)
                            if attachment_id and attachment_id.id:
                                self.write({
                                    'attachment_ids': [(6, 0, [attachment_id.id])],
                                    'downloaded': True,
                                })
                        elif attachment_id.datas != fileToBytes:
                            attachment_id.write({
                                'datas': fileToBytes,
                            })
                        if attachment_id.id not in self.attachment_ids.ids:
                            self.write({
                                'attachment_ids': [(6, 0, [attachment_id.id])],
                                'downloaded': True,
                            })
                else:
                    raise UserError("%s:\n%s\n%s" % (data.get('errorCode', 'Lỗi') , data.get('description',''),'Hóa đơn chưa ghi nhận trên hệ thống Viettel, hãy thử lại trong vài phút tới.'))
            else:
                raise UserError("Errors Get PDF: %s" % response['error'])
    
    def edit_invoice_info(self, data, type_name = "Edit", type_edit = "info", draft=False):
        invoice = self.sinvoice_id
        config_id = invoice.config_id
        headers = {
            'Accept': "application/json",
            'Content-Type': "application/json; charset=utf-8",
        }
        api_url = '/services/einvoiceapplication/api/InvoiceAPI/InvoiceWS/createInvoice/' + config_id.vsi_tin
        if draft:
            api_url = '/services/einvoiceapplication/api/InvoiceAPI/InvoiceUtilsWS/createInvoiceDraftPreview/' + config_id.vsi_tin

        result = config_id.execute_request(self, 'POST', api_url, headers=headers, data=data)
        if result.get("success", False):
            output = result['data']
            if not output['errorCode'] and not output['description']:
                if draft:
                    data = output
                    fileToBytes = data.get('fileToBytes')
                    filename = "%s_preview.pdf" % self.id
                    attachment_id = self.env['ir.attachment'].search([('res_model','=','viettel.sinvoice.line'),('res_id','=',self.id),('name','=',filename)],limit=1)
                    if not attachment_id:
                        attachment = {
                            'name': filename,
                            'datas': fileToBytes,
                            'res_model': 'viettel.sinvoice',
                            'res_id': self.id,
                        }
        
                        attachment_id = self.env['ir.attachment'].with_context(clean_context(self._context)).create(attachment)
                    else:
                        attachment_id.write({
                            'datas': fileToBytes,
                        })

                    return attachment_id

                transactionUuid = data.get("generalInvoiceInfo", {}).get('transactionUuid', {})
                info = output['result']
                if info:
                    self.write({
                        "state": type_edit,
                    })
                    invoice_type = type_edit=="replace" and type_edit or "adjusted" 
                    sinvoice_line_new = self.create({
                        "type": invoice_type,
                        "transactionID": info.get('transactionID'),
                        "transactionUuid": transactionUuid,
                        "supplierTaxCode": info.get('supplierTaxCode'),
                        "invoiceNo": info.get('invoiceNo'),
                        "reservationCode": info.get('reservationCode'),
                        "sinvoice_id":invoice.id,
                        "state": 'created',
                        "invoiceIssuedDate": datetime.now(),
                    })
                    if sinvoice_line_new:
                        sinvoice_line_new.action_get_invoices()

                    try:
                        self.get_invoice_pdf_file()
                    except Exception as e:
                        _logger.error("Lỗi tải lại hóa đơn %s", e)
                        pass
                        
                    return sinvoice_line_new
                else:
                    raise UserError('Created invoice draft')
            else:
                raise UserError("%s:\n%s" % (output['errorCode'] , output['description']))
        else:
            raise UserError("Edit invoice errors: %s" % result['error'])
    
    def get_invoice_input(self):
        # startDate = '%s%s'%(self.invoiceIssuedDate.strftime("%Y-%m-%dT%H:%M:%S"), '.000+07:00') #2019-11-05T10:14:32.611+07:00"
        # endDate = '%s%s'%(self.invoiceIssuedDate.strftime("%Y-%m-%dT%H:%M:%S"), '.999+07:00') 
        startDate = self.invoiceIssuedDate.strftime("%Y-%m-%d")
        endDate = (self.invoiceIssuedDate + relativedelta(days=1)).strftime("%Y-%m-%d")
        payload = {
            "startDate": startDate,
            "endDate": endDate,
            "rowPerPage": 10,
            "pageNum": 1,
            "templateCode": self.sinvoice_id.config_id.vsi_template,
            "invoiceNo": self.invoiceNo,
        }
        return payload
    
    
    def action_get_invoices(self):
        sinvoice_id = self.sinvoice_id
        config_id = sinvoice_id.config_id

        # if not sinvoice_id.invoiceNo:
        try:
            self.sinvoice_search_by_transaction_uuid()
        except Exception as e:
            _logger.error("########GET transactionID Errors: %s", e)
            pass

        headers = {
            'Accept': "application/json",
            'Content-Type': "application/json",
        }
        api_url = '/services/einvoiceapplication/api/InvoiceAPI/InvoiceUtilsWS/getInvoices/' + config_id.vsi_tin
        data = self.get_invoice_input()

        result = config_id.execute_request(self, 'POST', api_url, headers=headers, data=data)
        if result.get("success", False):
            output = result['data']
            if not output['errorCode'] and not output['description']:
                invoices = output['invoices']
                if invoices:
                    self.set_invoices_request(invoices)
                    try:
                        self.get_invoice_pdf_file()
                    except Exception as e:
                        pass
            else:
                raise UserError("%s:\n%s" % (output['errorCode'] , output['description']))
        else:
            raise UserError("Get invoice errors: %s" % result['error'])

    def sinvoice_search_by_transaction_uuid(self):
        if self.transactionUuid:
            config_id = self.sinvoice_id.config_id
            api_url = '/services/einvoiceapplication/api/InvoiceAPI/InvoiceWS/searchInvoiceByTransactionUuid'
            payload = {
                "supplierTaxCode": config_id.vsi_tin,
                "transactionUuid": self.transactionUuid,
            }
            headers = {
                "Content-type": "application/x-www-form-urlencoded",
            }
            response = config_id.execute_request(self,"POST", api_url, headers=headers, data=payload,  urlencoded=True)
            if response.get('success', False):
                data = response.get('data', {}) or {}
                if not data['errorCode']:
                    info = data['result'][0]
                    self.sinvoice_id.write({
                        'name': info.get('invoiceNo'),
                        'codeOfTax': info.get('codeOfTax'),
                        'exchangeDes': info.get('exchangeDes'),
                        'exchangeStatus': info.get('exchangeStatus'),
                    })
                    self.write({
                        'invoiceNo': info.get('invoiceNo'),
                    })
                else:
                    raise UserError("%s:\n%s" % (data['errorCode'] , data['description']))
            else:
                raise UserError("Sinvoice search errors: (%s)" % response['error'])


    def set_invoices_request(self, invoices):
        result_insert = []
        for invoice in invoices:
            invoiceIssuedDate = createTime = False
            if invoice.get('issueDateStr', False):
                invoiceIssuedDate = datetime.strptime(invoice.get('issueDateStr', False), "%Y-%m-%dT%H:%M:%SZ")
            if invoice.get('createTime',False):
                createTime = datetime.fromtimestamp(int(invoice.get('createTime',0)) / 1e3)
            if invoice.get('paymentTime', False) and invoice.get('paymentTime', False) != None:
                paymentTime = datetime.fromtimestamp(int(invoice.get('paymentTime', False)) / 1e3)
            else:
                paymentTime = False

            arr_type = {
                '1': 'original',
                '3': 'adjusted',
                '5': 'replace',
                '7': 'canceled',
                '9': 'adjusted_money'
            }
            inv_type = False
            if invoice.get('adjustmentType', False):
                inv_type = arr_type[str(invoice.get('adjustmentType', False))]
            
            invoice_data = {
                'invoiceId': invoice.get('invoiceId', False),
                'adjustmentType': invoice.get('adjustmentType', False),
                'templateCode': invoice.get('templateCode', False),
                'invoiceSeri': invoice.get('invoiceSeri', False),
                'invoiceNumber': invoice.get('invoiceNumber', False),
                'invoiceNo': invoice.get('invoiceNo', False),
                'currencyCode': invoice.get('currency', False),
                'total': invoice.get('total', False),
                'invoiceIssuedDate': invoiceIssuedDate,
                'vsi_status': invoice.get('state', False),
                'totalBeforeTax': invoice.get('totalBeforeTax', False),
                'taxAmount': invoice.get('taxAmount', False),
                'description': invoice.get('description', False),
                'buyerName': invoice.get('buyerName', False),
                'buyerTaxCode': invoice.get('buyerTaxCode', False),
                'buyerCode': invoice.get('buyerCode', False),
                'paymentStatus': invoice.get('paymentStatus', False),
                'createTime': createTime,
                'contractId': invoice.get('contractId', False),
                'contractNo': invoice.get('contractNo', False),
                'taxRate': invoice.get('taxRate', False),
                'paymentMethod': invoice.get('paymentMethod', False),
                'paymentTime': paymentTime,
                'customerId': invoice.get('customerId', False),
                'no': invoice.get('no', False),
                'type': inv_type,
            }
            invoice_type = self.env['viettel.sinvoice.type'].search([('code', '=', invoice.get('invoiceType', False))], limit=1)
            if invoice_type:
                invoice_data['invoiceType'] = invoice_type.id
            sinvoice_id = self.check_exist(invoice.get('invoiceNo', False))
            if sinvoice_id and len(sinvoice_id) > 0:
                sinvoice_id = sinvoice_id[0]
                sinvoice_id.write(invoice_data)
            else:
                sinvoice_id = self.create(invoice_data)
            if sinvoice_id and sinvoice_id.id:
                result_insert.append(sinvoice_id.id)
        return result_insert
    
    def get_request_data_cancel_sinvoice(self, data_cancel):
        invoice = self.sinvoice_id
        str_invoice_datetime = int(self.invoiceIssuedDate.timestamp()) * 1000
        data = {
            "supplierTaxCode": invoice.config_id.vsi_tin,
            "invoiceNo": self.invoiceNo,
            "templateCode": invoice.config_id.vsi_template,
            "strIssueDate": str_invoice_datetime,
            "additionalReferenceDesc": data_cancel.get('additionalReferenceDesc'),
            "additionalReferenceDate": data_cancel.get('additionalReferenceDate'),
        }
        return data
    
    def action_cancel_sinvoice(self, data_cancel = False):
        if data_cancel and self.state == 'created':
            invoice = self.sinvoice_id
            config_id = invoice.config_id
            api_url = '/services/einvoiceapplication/api/InvoiceAPI/InvoiceWS/cancelTransactionInvoice'
            data = self.get_request_data_cancel_sinvoice(data_cancel)
            headers = {
                "Content-type": "application/x-www-form-urlencoded",
            }
            result = config_id.execute_request(self, 'POST', api_url, headers=headers, params=data, urlencoded=True)
            if result.get('success', False):
                output = result['data']
                if not output['errorCode'] and output['description'] == 'CANCEL TRANSACTION INVOICE SUCCESS':
                    self.write({
                        'state': 'canceled',
                        'description': output['description'],
                        'vsi_reference_desc': data_cancel.get('additionalReferenceDesc'),
                        'vsi_reference_date': data_cancel.get('additionalReferenceDate'),
                        'reason': data_cancel.get('reason'),
                        'type': 'canceled',
                    })
                    time.sleep(3)
                    try:
                        self.get_invoice_pdf_file()
                    except Exception as e:
                        pass
                else:
                    raise UserError("%s:\n%s" % (output['errorCode'] , output['description']))
            else:
                raise UserError("Cancel errors: %s" % result['error'])