# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
import requests
import json
from odoo.exceptions import UserError
rowPerPage = 10 # Số dòng trên một trang. Do webservice thực hiện phân trang nên Maxlength : 18

class ViettelSInvoiceLookups(models.Model):
    _name = 'viettel.sinvoice.lookups'
    _description = 'Viettel S-Invoice Lookups'
    
    name = fields.Char(string='Name')
    date_start = fields.Datetime('Date start')
    date_end = fields.Datetime('Date end')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    vsi_tin = fields.Char(related='company_id.vsi_tin', store=True, related_sudo=False)
    vsi_series = fields.Char(related='company_id.vsi_series', store=True, related_sudo=False)
    vsi_template = fields.Char(related='company_id.vsi_template', store=True, related_sudo=False)
    sinvoice_type = fields.Selection([
        ('original', 'Invoice Original'), #Hóa đơn gốc
        ("adjusted", "Invoice adjusted"), #Hóa đơn điều chỉnh
        ("replace", "Invoice replace"), #Hóa đơn thay thế
        ("canceled", 'Invoice canceled'), #Hóa đơn xóa bỏ
    ], string='Hình thức hóa đơn', default='original')
    
    buyer_node = fields.Char('Buyer Code')
    buyer_name = fields.Char('Buyer Name')
    buyer_tax_code = fields.Char('Buyer Tax Code')
    sinvoice_ids = fields.Many2many('viettel.sinvoice.line', 'lookups_sinvoice_line_rel','lookup_id', 'sinvoice_id', 'SInvoice lines')
    invoice_no = fields.Char('Invoice No')
    buyer_code = fields.Char("buyer Code")
    contractNo = fields.Char("contract No")
    contractId = fields.Char("contract Id")
    customerId = fields.Char("customer Id")
    buyerIdNo = fields.Char("buyer Id No")
    invoiceType = fields.Many2one('viettel.sinvoice.type', 'Type') #Mã loại hóa đơn
    getAll = fields.Boolean("getAll")
    
    def get_invoice_input(self, pageNum = 1):
        startDate = '%s%s'%(self.date_start.strftime("%Y-%m-%dT%H:%M:%S"), '.000+07:00') #format: 2019-11-05T10:14:32.611+07:00"
        endDate = '%s%s'%(self.date_end.strftime("%Y-%m-%dT%H:%M:%S"), '.999+07:00') 
        payload = {
            "startDate": startDate,
            "endDate": endDate,
            "rowPerPage": rowPerPage,
            "pageNum": pageNum,
            "templateCode": self.company_id.vsi_template,
            
        }
        if self.invoice_no and self.invoice_no !='':
            payload['invoiceNo'] = self.invoice_no
        
        if self.invoiceType and self.invoiceType.code !='':
            payload['invoiceType'] = self.invoiceType.code
        
        if self.buyer_name and self.buyer_name !='':
            payload['buyerName'] = self.buyer_name
            
        if self.getAll:
            payload['getAll'] = self.getAll
        
        
        
        if self.contractNo:
            payload.update({
                "buyerTaxCode": self.buyer_tax_code,
                "contractNo": self.contractNo,
                "contractId": self.contractId,
                "customerId": self.customerId,
                "buyerIdNo": self.buyerIdNo,
            })
            
        return payload
    
    
    def action_search_sinvoice(self):
        self.write({'sinvoice_ids': [(6, 0, [])],})
        results_insert = self.get_all_sinvoice()
        if results_insert:
            self.write({
                'sinvoice_ids': [(6, 0, results_insert)],
            })
        
    def get_all_sinvoice(self, pageNum = 1,results_insert = []):
        headers = {
            'Accept': "application/json",
            'Content-Type': "application/json",
        }
        company_id = self.company_id
        api_url = company_id.vsi_domain + '/InvoiceAPI/InvoiceUtilsWS/getInvoices/' + company_id.vsi_tin
        data = self.get_invoice_input(pageNum)
        result = requests.post(api_url, data=json.dumps(data), headers=headers, auth=(company_id.vsi_username, company_id.vsi_password))
        if result.status_code == 200:
            output = json.loads(result.text)
            if not output['errorCode'] and not output['description']:
                invoices = output['invoices']
                if invoices:
                    results = self.env['viettel.sinvoice.line'].set_invoices_request(invoices)
                    results_insert.extend(results)
                if (pageNum * rowPerPage) < int(output['totalRow']):
                    return self.get_all_sinvoice(pageNum + 1)
                else:
                    return results_insert
            else:
                raise UserError("%s:\n%s" % (output['errorCode'] , output['description']))
        else:
            raise UserError("Connection errors: %s" % result.status_code)
        
        