data = {
    "generalInvoiceInfo": {  # Hoá đơn thông thường
        "invoiceType": "01GTKT",
        "templateCode": "01GTKT0/001",
        "invoiceSeries": "AB/18E",
        "invoiceIssuedDate": 1543842113042,
        "currencyCode": "VND",
        "adjustmentType": "1",
        "paymentStatus": True,
        "cusGetInvoiceRight": True,
        "userName": "1000317707"},
    "buyerInfo": {},
    "sellerInfo": {},
    "extAttribute": [],
    "payments": [],
    "deliveryInfo": {},
    "itemInfo": [],
    "metadata": [],
    "meterReading": [],
    "summarizeInfo": {},
    "taxBreakdowns": []
}
# Hoá đơn điều chỉnh tiền
generalInvoiceInfo = {
    "invoiceType": "01GTKT",
    "templateCode": "01GTKT0/383",
    "invoiceSeries": "AB/18E",
    "invoiceIssuedDate": 1544152232729,
    "invoiceSignedDate": 1544152232729,
    "currencyCode": "VND",
    "adjustmentType": "5",
    "adjustmentInvoiceType": "1",
    "originalInvoiceId": "AB/18E0000036",
    "originalInvoiceIssueDate": 1544152198000,
    "additionalReferenceDesc": "Văn bản",
    "additionalReferenceDate": 1544115600000,
    "paymentStatus": True,
    "cusGetInvoiceRight": True,
    "userName": "test7"
  }
# Hoá đơn điều chỉnh thông tin
generalInvoiceInfo = {
    "invoiceType": "01GTKT",
    "templateCode": "01GTKT0/383",
    "invoiceSeries": "AB/18E",
    "invoiceIssuedDate": 1544152232729,
    "invoiceSignedDate": 1544152232729,
    "currencyCode": "VND",
    "adjustmentType": "5",
    "adjustmentInvoiceType": "2",
    "originalInvoiceId": "AB/18E0000036",
    "originalInvoiceIssueDate": 1544152198000,
    "additionalReferenceDesc": "Văn bản",
    "additionalReferenceDate": 1544115600000,
    "paymentStatus": True,
    "cusGetInvoiceRight": True,
    "userName": "test7"
  }
# Hóa đơn thay thế
generalInvoiceInfo = {
    "invoiceType": "01GTKT",
    "templateCode": "01GTKT0/383",
    "invoiceSeries": "AB/18E",
    "invoiceIssuedDate": 1544157807809,
    "invoiceSignedDate": 1544157807809,
    "currencyCode": "VND",
    "adjustmentType": "3",
    "originalInvoiceId": "AB/18E0000037",
    "originalInvoiceIssueDate": 1544152202000,
    "additionalReferenceDesc": "Văn bản",
    "additionalReferenceDate": 1544115600000,
    "paymentStatus": True,
    "cusGetInvoiceRight": True,
    "userName": "test7"
  }

example_data = {
    'itemInfo': [{
        'lineNumber': 1,
        'itemCode': 'product_13',
        'itemName': 'Customizable Desk',
        'unitName': 'Unit(s)',
        'unitPrice': 800.4,
        'quantity': 1.0,
        'itemTotalAmountWithoutTax': 800.0,
        'itemTotalAmountWithTax': 880.0,
        'itemTotalAmountAfterDiscount': 880.0,
        'taxAmount': 80.0,
        'taxPercentage': 10.0
    }],
    'generalInvoiceInfo': {
        'transactionUuid': 'ee7fe2c0-547f-11eb-8d23-6067204f1988',
        'userName': 'Mitchell Admin',
        'currencyCode': 'VND',
        'invoiceIssuedDate': 1610419400000,
        'invoiceSignedDate': 1610419400000,
        'templateCode': '01GTKT0/001',
        'invoiceSeries': 'AB/18E',
        'invoiceType': '01GTKT',
        'paymentType': 'TM/CK',
        'paymentTypeName': 'TM/CK',
        'paymentStatus': 1,
        'adjustmentType': 1
    },
    'buyerInfo': {
        'buyerName': '',
        'buyerLegalName': 'Minh',
        'buyerAddressLine': '123879123 82309 bac kabn',
        'buyerCode': '',
        'buyerTaxCode': '121231232'
    },
    'summarizeInfo': {
        'sumOfTotalLineAmountWithoutTax': 800.0,
        'totalTaxAmount': 80.0,
        'totalAmountWithoutTax': 800.0,
        'totalAmountWithTax': 880.0,
        'discountAmount': 0
    },
    'taxBreakdowns': [{
        'taxPercentage': 10.0,
        'taxableAmount': 800.0,
        'taxAmount': 80.0
    }],
    'payments': [{
        'paymentMethodName': 'TM/CK'
    }]
}

from datetime import datetime
from odoo import models, fields, api,_
import requests
import json
from odoo.exceptions import UserError

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    vsi_status = fields.Selection([
        ('created', 'Đã tạo trên S-INVOICE'),
        ('canceled', 'Đã hủy trên S-INVOICE'),
        ], string=u'Trạng thái S-INVOICE', copy=False)

    def create_invoice_vninvoice(self, invoice):
        invoiceDetails = []
        lineNumber = 0
        breakdown = {}
        for invoice_line in invoice.invoice_line_ids:
            taxAmount = invoice_line.price_total - invoice_line.price_subtotal
            lineNumber += 1
            line_data = {
                "lineNumber": lineNumber,
                "itemCode": "product_" + str(invoice_line.product_id.id),
                "itemName": invoice_line.product_id.name,
                "unitName":  invoice_line.product_id.uom_id.name,
                "unitPrice": invoice_line.price_unit,
                "quantity": invoice_line.quantity,
                "itemTotalAmountWithoutTax": invoice_line.price_subtotal,
                "taxAmount": taxAmount,
            }
            if len(invoice_line.invoice_line_tax_ids):
                for tax_id in invoice_line.invoice_line_tax_ids:
                    if tax_id.id not in breakdown:
                        breakdown[tax_id.id] = {
                            "taxPercentage": tax_id.amount,
                            "taxableAmount": invoice_line.price_subtotal,
                            "taxAmount": invoice_line.price_subtotal * tax_id.amount / 100,
                        }
                    else:
                        breakdown[tax_id.id]["taxableAmount"] += invoice_line.price_subtotal
                        breakdown[tax_id.id]["taxAmount"] += invoice_line.price_subtotal * tax_id.amount / 100
                    line_data["taxPercentage"] = tax_id.amount
                    break

            invoiceDetails.append(line_data)

        generalInvoiceInfo = {
            "transactionUuid": invoice.access_token,
            "userName": invoice.user_id.name,
            "currencyCode": invoice.currency_id.name,
            "invoiceIssuedDate": int(datetime.strptime(invoice.date_invoice, '%Y-%m-%d').timestamp()) * 1000,
            "templateCode": invoice.company_id.vsi_template,  # config
            "invoiceSeries": invoice.company_id.vsi_series,  # config
            "invoiceType": invoice.company_id.vsi_type.code,  # config
            "paymentType": "TM/CK",
            "paymentTypeName": "TM/CK",
            "paymentStatus": True,
            "adjustmentType": 1,
        }

        payments = [{
            "paymentMethodName": "TM/CK",
        }]

        buyerInfo = {
            "buyerEmail": invoice.partner_id.email,
            "buyerLegalName": invoice.partner_id.name,
            "buyerTaxCode": invoice.partner_id.vat[2:],
            "buyerAddressLine": "%s, %s, %s" % (invoice.partner_id.street, invoice.partner_id.street2, invoice.partner_id.city),
        }

        summarizeInfo = {
            "sumOfTotalLineAmountWithoutTax": invoice.amount_untaxed,
            "totalTaxAmount": invoice.amount_tax,
            "totalAmountWithoutTax": invoice.amount_untaxed,
            "totalAmountWithTax": invoice.amount_total,
            "discountAmount": 0,
        }

        taxBreakdowns = []
        for bd in breakdown:
            taxBreakdowns.append(breakdown[bd])

        data = {
            "itemInfo": invoiceDetails,
            "generalInvoiceInfo": generalInvoiceInfo,
            "buyerInfo": buyerInfo,
            "summarizeInfo": summarizeInfo,
            "taxBreakdowns": taxBreakdowns,
            "payments": payments,
        }
        return data

    @api.multi
    def do_create_draft_invoice(self):
         self.create_invoice(draft=True)

    @api.multi
    def do_create_invoice(self):
        if not self.date_invoice:
            raise UserError('Phải nhập ngày phát hành hóa đơn')
            return
        if not self.vsi_status:
            self.create_invoice(draft=False)

    @api.multi
    def create_invoice(self, draft=False):
        headers = {"Content-type": "application/json; charset=utf-8"}
        company_id = self.company_id
        if draft:
            api_url = company_id.vsi_domain + '/InvoiceAPI/InvoiceWS/createOrUpdateInvoiceDraft/' + company_id.vsi_tin
        else:
            api_url = company_id.vsi_domain + '/InvoiceAPI/InvoiceWS/createInvoice/' + company_id.vsi_tin
        data = self.create_invoice_vninvoice(self)
        # jsondata = json.dumps(data)
        result = requests.post(api_url, json=data, headers=headers, auth=(company_id.vsi_username, company_id.vsi_password))

        if result.status_code == 200:
            output = json.loads(result.text)
            if not output['errorCode'] and not output['description']:
                info = output['result']
                if info:
                    self.write({
                        'vsi_status': 'created',
                        'reference': info['invoiceNo'] + ' - ' + info['reservationCode'],
                        'name': info['invoiceNo'],
                    })
                else:
                    raise UserError('Đã tạo hóa đơn nháp')
            else:
                raise UserError("%s:\n%s" % (output['errorCode'] , output['description']))
        else:
            raise UserError("Lỗi Kết Nối: %s" % result.status_code)

