# -*- coding: utf-8 -*-
from datetime import datetime
import time
from odoo import models, fields, api,_
import json
from odoo.exceptions import UserError,ValidationError
import uuid
from threading import Timer
import logging

TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}
from ..redis import Redis
_logger = logging.getLogger(__name__)

class ViettelSinvoice(models.Model):
    _name = "viettel.sinvoice"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Viettel S-Invoice"
    _order = "create_date desc"

    @api.model
    def _default_item_type_set_id(self):
        return self.env['viettel.sinvoice.item.type.set'].search([('is_default', '=', True), ('active', '=', True)], limit=1)
    
    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', [TYPE2JOURNAL[ty] for ty in inv_types if ty in TYPE2JOURNAL]),
            ('company_id', '=', company_id),
        ]
        company_currency_id = self.env['res.company'].browse(company_id).currency_id.id
        currency_id = self._context.get('default_currency_id') or company_currency_id
        currency_clause = [('currency_id', '=', currency_id)]
        if currency_id == company_currency_id:
            currency_clause = ['|', ('currency_id', '=', False)] + currency_clause
        return (
            self.env['account.journal'].search(domain + currency_clause, limit=1)
            or self.env['account.journal'].search(domain, limit=1)
        )
    
    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id or self.env.user.company_id.currency_id
    
    invoice_id = fields.Many2one('account.move', string='Invoice erp',)
    company_id = fields.Many2one('res.company', string='Company',readonly=True, default=lambda self: self.env['res.company']._company_default_get('account.move'))
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True, default=lambda self: self.env.user, copy=False)
    name = fields.Char(string='Reference/Description', copy=False)
    currency_id = fields.Many2one('res.currency', string='Currency',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_currency, tracking=True)
    partner_vat_id = fields.Many2one('res.partner', 'Customer')
    sinvoice_data_ids = fields.One2many('viettel.sinvoice.data', 'sinvoice_id')#Dữ liệu để đẩy lên
    sinvoice_line_ids = fields.One2many('viettel.sinvoice.line','sinvoice_id','Invoice Edit')#Các hóa đơn điện tử đã phát hành
    date_invoice = fields.Date(string='Invoice Date', index=True, copy=False)
    date = fields.Date(string='Accounting Date', copy=False)
    partner_vat_name = fields.Char('Buyer Name')
    partner_vat = fields.Char('VAT')
    partner_vat_address = fields.Char('Invoiced address')

    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency", readonly=True)
    type = fields.Selection([
            ('entry', 'Journal Entry'),
            ('out_invoice', 'Customer Invoice'),
            ('out_refund', 'Customer Credit Note'),
            ('in_invoice', 'Vendor Bill'),
            ('in_refund', 'Vendor Credit Note'),
            ('out_receipt', 'Sales Receipt'),
            ('in_receipt', 'Purchase Receipt'),
        ], readonly=True, states={'draft': [('readonly', False)]}, index=True, change_default=True,
        default=lambda self: self._context.get('type', 'out_invoice'),
        tracking=True)
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', 
        readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
                    ('draft', 'Original invoice'),
                    ('comfirm', 'Comfirm'),
                    ('created', 'Published'),
                    ('canceled', 'Canceled'),
                    ('info', 'Change info'),
                    ('amount', 'Change amount'),
                    ('replace', 'Replace invoice'),
                ], string='Status', copy=False, default='draft', tracking=True)
    reservationCode = fields.Char('Reservation Code')
    transactionID = fields.Char('Transaction ID')
    transactionUuid = fields.Char("Transaction Uuid", copy=False)
    invoiceIssuedDate = fields.Datetime('Invoice Issued Date', copy=False)
    issue_draft = fields.Boolean(string="Issue draft", default=False)
    config_id = fields.Many2one('viettel.sinvoice.config','Sinvoice configure')
    item_type_set_id = fields.Many2one(
        'viettel.sinvoice.item.type.set',
        string='Thông tư áp dụng sản phẩm',
        default=_default_item_type_set_id,
    )
    vsi_type_id = fields.Many2one('viettel.sinvoice.type', related='config_id.vsi_type')
    vsi_type_code = fields.Char(related='vsi_type_id.odoo_code')

    attachment_ids = fields.Many2many('ir.attachment', 'sinvoice_ir_attachments_rel',
        'sinvoice_id', 'attachment_id', string='Attachments', compute="_compute_attachments")

    einvoice_status = fields.Selection([
        ('draft', 'Original invoice'),
        ('created', 'Published'),
        ('canceled', 'Invoice Canceled'),
        ('info', 'Modified information'),
        ('amount', 'Money adjusted'),
        ('replace', 'Invoice is replaced')
        ],string="Einvoice Status",compute="_compute_get_einvoice_status")

    economicContractNo = fields.Char('Lệnh điều động nội bộ')
    transformer = fields.Char('Tên người vận chuyển')
    vehicle = fields.Char('Phương tiện vận chuyển')
    contractNo = fields.Char('Hợp đồng số')
    HVTNXHang = fields.Char('Họ và tên người xuất hàng')
    KPTQuan = fields.Char('Thể hiện mẫu phi thuế quan')
    commandDate = fields.Date(string="Ngày hiệu lực")
    exportAt = fields.Char(string=" Xuất tại kho")
    importAt = fields.Char(string=" Nhập tại kho")

    codeOfTax = fields.Char("SInvoice Code of Tax", copy=False)
    exchangeStatus = fields.Char("SInvoice Exchange Status", copy=False)
    exchangeDes = fields.Char("SInvoice Exchange Des", copy=False)

    adjust_invoice_ids = fields.One2many('account.move', 'sinvoice_adjust_id', 'Odoo invoice adjusted')
    count_adjust_invoice = fields.Integer(compute='compute_adjust_inv_count')

    @api.depends('adjust_invoice_ids')
    def compute_adjust_inv_count(self):
        for res in self:
            res.count_adjust_invoice = len(res.adjust_invoice_ids)

    def open_invoice_adjustment(self):
        return {
            'name': _("Invoice adjusted"),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id','in', self.adjust_invoice_ids.ids)]
        }

    @api.depends('sinvoice_line_ids','sinvoice_line_ids.state')
    def _compute_get_einvoice_status(self):
        for res in self:
            if not res.sinvoice_line_ids:
                if res.issue_draft:
                    res.einvoice_status = 'draft'
                else:
                    res.einvoice_status = False
            else:
                canceled = res.sinvoice_line_ids.filtered(lambda x: x.state == 'canceled')
                if canceled:
                    res.einvoice_status = 'canceled'
                else:
                    # Handle both saved records (with integer IDs) and new records (with NewId objects)
                    lines = res.sinvoice_line_ids.sorted(key=lambda x: x.id if isinstance(x.id, int) else 0)
                    res.einvoice_status = lines[0].state

    @api.depends('sinvoice_line_ids')
    def _compute_attachments(self):
        for record in self:
            if record.sinvoice_line_ids:
                record.attachment_ids = [(6, 0, record.sinvoice_line_ids.mapped('attachment_ids').ids)]
            else:
                record.attachment_ids = [(6, 0, [])]

    def get_partner_address(self, partner):
        address = ''
        if partner:
            if partner.street:
                address += partner.street
            if partner.wards_id:
                address += len(address) > 0 and ', ' + partner.wards_id.name or partner.wards_id.name
            if partner.district_id:
                address += len(address) > 0 and ', ' + partner.district_id.name or partner.district_id.name
            if partner.state_id:
                address += len(address) > 0 and ', ' + partner.state_id.name or partner.state_id.name
            if partner.country_id:
                address += len(address) > 0 and ', ' + partner.country_id.name or partner.country_id.name
        return address

    @api.onchange('partner_vat_id')    
    def change_id_partner_vat(self):
        self.partner_vat = self.partner_vat_id.vat or ''
        self.partner_vat_address = self.partner_vat_id.address_invoice_vat
        self.partner_vat_name = self.partner_vat_id.name_vat
    
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Credit Note'),
            'in_refund': _('Vendor Credit note'),
        }
        result = []
        for inv in self:
            result.append((inv.id, "%s" % (inv.name or TYPES[inv.type])))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        invoice_ids = []
        if name:
            invoice_ids = self._search([('name', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid)
        if not invoice_ids:
            invoice_ids = self._search([('name', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
        return self.browse(invoice_ids).name_get()
    
    def action_create_invoice(self):
        self.create_invoice(draft=False)
    
    def action_create_draft_invoice(self):
        try:
            self.create_invoice(draft=True)
            self.write({'issue_draft':True})
        except ValueError:
            raise UserError(ValueError)
        
    def action_confirm(self):
        if not self.partner_vat_id or  not self.partner_vat_address:
            raise ValidationError(_('Customer information is missing, Please check again!!!'))

        self.write({'state':'comfirm'})

    def action_draft(self):
        self.write({'state':'draft'})
    
    def create_invoice(self, draft=False):
        redis = Redis()
        redis_key = 'create_invoice:%s-%s' % (self.id, draft)
        cache_key = redis.get(redis_key)
        _logger.info("############### cache_key %s-%s", redis_key, cache_key)
        if cache_key:
            return True

        redis.set(
            key=redis_key,
            data='create_invoice %s' % self.id,
            ex=60
        )

        try:
            self = self.with_context(lang=self.env.user.lang)

            config_id = self.config_id
            if not self.partner_vat_id:
                raise UserError(_("Please select an invoice customer"))

            invoiceIssuedDate = datetime.now()
            self.write({"invoiceIssuedDate": invoiceIssuedDate})
            
            headers = {
                'Content-Type': 'application/json'
            }
            api_url = '/services/einvoiceapplication/api/InvoiceAPI/InvoiceWS/createInvoice/' + config_id.vsi_tin
            if draft:
                api_url = '/services/einvoiceapplication/api/InvoiceAPI/InvoiceWS/createOrUpdateInvoiceDraft/' + config_id.vsi_tin

            data = self.get_post_data_sinvoice()

            result = config_id.execute_request(self, 'POST', api_url, headers=headers ,data=data)
            if result.get('success', False):
                output = result['data'] or {}
                if not output.get('errorCode', False):
                    info = output.get('result', False)
                    transactionUuid = data.get("generalInvoiceInfo", {}).get('transactionUuid', {})
                    if info:
                        self.write({
                            'state': 'created',
                            'transactionUuid': transactionUuid,
                            'name': info.get('invoiceNo', False),
                            'reservationCode': info.get('reservationCode', False),
                            'transactionID': info.get('transactionID', False),
                        })
                        sinvoice_line_new = self.env['viettel.sinvoice.line'].create({
                            "type": "original",
                            "transactionID": info.get('transactionID', False),
                            'transactionUuid': transactionUuid,
                            "supplierTaxCode": info.get('supplierTaxCode', False),
                            "invoiceNo": info.get('invoiceNo', False),
                            "reservationCode": info.get('reservationCode', False),
                            "sinvoice_id": self.id,
                            "invoiceIssuedDate": invoiceIssuedDate,
                            "state": 'created',
                            "originalInvoiceIssueDate": invoiceIssuedDate,
                        })

                        t = Timer(3.0, sinvoice_line_new._pepare_do_get_invoice)
                        t.start()

                    elif not draft:
                        self.write({
                            'state': 'draft',
                        })
                else:
                    redis.flush(redis_key)
                    raise UserError("%s:\n%s" % (output['errorCode'] , output.get('description', '')))
            else:
                redis.flush(redis_key)
                raise UserError("Connection errors: %s" % result['error'])

        except Exception as e:
            redis.flush(redis_key)
            raise UserError(e)
    
    def get_metadata(self):
        metadata = []
        code = self.vsi_type_code
        if code in ['03XKNB','04HGDL', '07KPTQ']:
            if code in ['04HGDL','03XKNB']:
                filter_list = [
                    'economicContractNo',
                    'transformer',
                    'vehicle',
                    'contractNo',
                    'HVTNXHang',
                ]
                data={
                    'economicContractNo': self.economicContractNo or '',
                    'transformer': self.transformer or '',
                    'vehicle': self.vehicle or '',
                    'contractNo': self.contractNo or '',
                    'HVTNXHang': self.HVTNXHang or '',
                }
                if self.commandDate:
                    commandDate_str = str(self.commandDate.strftime("%Y-%m-%d %H:%M:%S"))
                    commandDate = int(datetime.strptime(commandDate_str, "%Y-%m-%d %H:%M:%S").timestamp()) * 1000
                    data['commandDate'] = commandDate
                    filter_list += ['commandDate']

            if code == '07KPTQ':
                filter_list = [
                    'KPTQuan'
                ]
                data = {
                    'KPTQuan': self.KPTQuan or '',
                }
   
            for field_id in self.config_id.vsi_type.customer_field_ids.filtered(lambda m: m.keyTag in filter_list):
                input_data = {
                    "invoiceCustomFieldId": int(field_id.field_id),
                    "keyTag": field_id.keyTag,
                    "valueType": field_id.valueType,
                    "keyLabel": field_id.keyLabel,
                }
                if field_id.valueType == "text":
                    input_data['stringValue'] = data.get(field_id.keyTag)
                if field_id.valueType == "date":
                    input_data['dateValue'] = data.get(field_id.keyTag)
                metadata += [input_data]
        return metadata

    def get_post_data_sinvoice(self, invoiceIssuedDate=False):
        data = False
        error = False
        invoiceDetails = self.get_invoice_details()
        if not invoiceDetails:
            error = _('invoiceDetails is NULL!')
        generalInvoiceInfo = self.get_generalInvoiceInfo(invoiceIssuedDate=invoiceIssuedDate)
        if not generalInvoiceInfo:
            error = _('generalInvoiceInfo is NULL!')
        buyerInfo = self.get_buyerInfo()
        if not buyerInfo:
            error = _('buyerInfo is NULL!')
        summarizeInfo = self.get_summarize_info(invoiceDetails)
        if not summarizeInfo:
            error = _('summarizeInfo is NULL!')
        if error:
            raise UserError(error)
            return False
        else:
            taxBreakdowns = []
            breakdown = self.get_breakdown()
            for bd in breakdown:
                taxBreakdowns.append(breakdown[bd])
            payments = self.get_payments()
            metadata = self.get_metadata()
            data = {
                "itemInfo": invoiceDetails,
                "generalInvoiceInfo": generalInvoiceInfo,
                "buyerInfo": buyerInfo,
                "summarizeInfo": summarizeInfo,
                "taxBreakdowns": taxBreakdowns,
                "payments": payments,
                "metadata": metadata,
            }
        return data

    def _get_default_item_type_for_line(self, invoice_line):
        if invoice_line.display_type in ('line_note', 'line_section'):
            return 'ghi_chu'
            
        if invoice_line.product_id:
            detailed_type = getattr(invoice_line.product_id, 'detailed_type', False) or getattr(invoice_line.product_id, 'type', False)
            if detailed_type in ['product', 'consu', 'service']:
                return 'hang_hoa'
        return 'hang_hoa'

    def _convert_selection_key(self, key_value):
        if key_value in [False, None, '']:
            return False
        try:
            return int(key_value)
        except Exception:
            return False
    
    def _check_has_mixed_item_types(self):
        """Kiểm tra xem sinvoice có cả dòng hàng hóa lẫn dòng chiết khấu không."""
        item_types = set()
        for line in self.sinvoice_data_ids:
            if line.product_id:
                it = line.vsi_item_type or self._get_default_item_type_for_line(line)
                item_types.add(it)
        return 'chiet_khau' in item_types and len(item_types - {'chiet_khau'}) > 0

    def get_invoice_details(self, sinvoice_edit_type = False, invoiceIssuedDate = False):
        config_id = self.config_id
        mapping_dict = self.item_type_set_id.get_mapping_dict() if self.item_type_set_id else {}
        invoiceDetails = []
        lineNumber = 0
        note_increase = []
        amount_total = 0
        has_mixed_types = self._check_has_mixed_item_types()
        for invoice_line in self.sinvoice_data_ids:
            lineNumber += 1
            data = None
            item_type = invoice_line.vsi_item_type or self._get_default_item_type_for_line(invoice_line)
            selection_key = self._convert_selection_key(mapping_dict.get(item_type))
            if invoice_line.product_id:
                data = {
                    "lineNumber": lineNumber,
                    "itemCode": "product_" + str(invoice_line.product_id.id),
                    "itemName": invoice_line.name or '',
                    "unitName":  invoice_line.product_uom_id and invoice_line.product_uom_id.name or '',
                    "unitPrice": round(invoice_line.price_unit, 2),
                    "quantity": round(invoice_line.quantity,3),
                    "itemTotalAmountWithoutTax": round(invoice_line.price_subtotal,2),
                    "itemTotalAmountWithTax": round(invoice_line.price_total,  2),
                    "itemTotalAmountAfterDiscount": round(invoice_line.price_subtotal, 2),
                    "taxAmount": round(invoice_line.price_tax, 2),
                    "discount2": round(invoice_line.discount, 2)
                }
                if selection_key is not False and not sinvoice_edit_type:
                    data['selection'] = selection_key
                if len(invoice_line.tax_ids): #Thuế
                    for tax_id in invoice_line.tax_ids:
                        if tax_id.not_taxable:
                            data['taxPercentage'] = -2
                        elif tax_id.not_declared_paid:
                            data['taxPercentage'] =  -1
                        else:
                            data["taxPercentage"] = tax_id.amount
                        
                        break
                else:
                    data["taxPercentage"] = 0
                
                if invoice_line.discount > 0: #Hàng hóa có chiết khấu trên dòng sản phẩm
                    data["discount"] = invoice_line.discount
                    data["itemDiscount"] = invoice_line.price_unit * invoice_line.quantity * invoice_line.discount / 100

                if item_type == 'chiet_khau':
                    if has_mixed_types:
                        # Hóa đơn hỗn hợp: chiết khấu là dòng giảm trừ
                        data["isIncreaseItem"] = False
                        # Đảm bảo giá trị gửi Viettel luôn dương
                        # (xử lý cả 2 trường hợp: price_unit âm hoặc quantity âm)
                        data["unitPrice"] = abs(data["unitPrice"])
                        data["quantity"] = abs(data["quantity"])
                        data["itemTotalAmountWithoutTax"] = abs(data["itemTotalAmountWithoutTax"])
                        data["itemTotalAmountWithTax"] = abs(data["itemTotalAmountWithTax"])
                        data["itemTotalAmountAfterDiscount"] = abs(data["itemTotalAmountAfterDiscount"])
                        data["taxAmount"] = abs(data["taxAmount"])
                    else:
                        # Hóa đơn chiết khấu riêng biệt: giữ nguyên hành vi cũ
                        data["isIncreaseItem"] = True
                 
                if sinvoice_edit_type == 'amount':
                    if invoice_line.edit_type in ["increase", "reduction",'reduction_price']:
                        if invoice_line.edit_type == 'increase':
                            isIncreaseItem = True
                            edit_type = _('increase')
                            if edit_type not in note_increase:
                                note_increase.append(edit_type)
                                product_name_start = _("Adjusting increase the amount of goods and tax on goods/services: ")
                        else:
                            isIncreaseItem = False
                            edit_type = _("reduction")
                            if edit_type not in note_increase:
                                note_increase.append(edit_type)
                                product_name_start = _("Adjusting reducing the amount of goods and tax on goods/services: ")

                            if config_id.vsi_uncheck_data:
                                data['itemTotalAmountWithoutTax'] = - data['itemTotalAmountWithoutTax']
                                data['itemTotalAmountWithTax'] = - data['itemTotalAmountWithTax']
                                data['itemTotalAmountAfterDiscount'] = - data['itemTotalAmountAfterDiscount']

                            if invoice_line.edit_type  == 'reduction':
                                data['quantity'] = - data['quantity']
                            else:
                                data['unitPrice'] = - data['unitPrice']
                                
                        # data["itemName"] = "%s%s" % (product_name_start, invoice_line.name)
                        data["itemName"] = invoice_line.name
                        data["isIncreaseItem"] = isIncreaseItem
                        data["adjustmentTaxAmount"] = 1
                    else:
                        data = False
            else:
                if invoice_line.display_type:
                    data = {
                        "itemName": invoice_line.name or ''
                    }
                    if selection_key is not False:
                        data["selection"] = selection_key
                    else:
                        data["selection"] = 2
                if sinvoice_edit_type == 'amount':
                    data["isIncreaseItem"] = False
                    
            if data:
                invoiceDetails.append(data)
                amount_total += invoice_line.price_total
                
        # if len(invoiceDetails) > 0:
        #     if sinvoice_edit_type == 'amount':
        #         #Ghi chú Hóa đơn điều chỉnh tiền
        #         line_data = {
        #           "selection": 2,
        #           "itemName": _("Điều chỉnh %stiền hàng, tiền thuế cho hóa đơn điện tử số %s lập ngày %s số tiền: %s") %(note_increase and "%s "%'/'.join(note_increase) or "", self.name, invoiceIssuedDate, amount_total)
        #         }
        #         invoiceDetails.append(line_data)
                 
        #     elif sinvoice_edit_type == 'replace':
        #         #Ghi chú Hóa đơn thay thế
        #         line_data = {
        #           "selection": 2,
        #           "itemName": "Hóa đơn thay thế cho số hóa đơn điện tử %s ngày %s" %(self.name, invoiceIssuedDate)
        #         }
        #         invoiceDetails.append(line_data)
        # else:
        #     raise UserError(_('Invoice line is NULL!'))
        #     return False
        return invoiceDetails
     
    def get_summarize_info(self, invoiceDetails):
        summarizeInfo = False
        if invoiceDetails:
            sumOfTotalLineAmountWithoutTax = 0
            totalTaxAmount = 0
            totalAmountWithoutTax = 0
            totalAmountWithTax = 0
            totalDiscountAmount = 0
            for invoiceDetail in invoiceDetails:
                if invoiceDetail.get('unitPrice') and invoiceDetail.get('quantity'):
                    amt_without_tax = abs(invoiceDetail.get('itemTotalAmountWithoutTax') or 0)
                    tax_amt = abs(invoiceDetail.get('taxAmount') or 0)
                    amt_with_tax = abs(invoiceDetail.get('itemTotalAmountWithTax') or 0)
                    # Nếu isIncreaseItem == False (dòng chiết khấu trong hóa đơn hỗn hợp): trừ
                    if 'isIncreaseItem' in invoiceDetail and invoiceDetail.get('isIncreaseItem') == False:
                        sumOfTotalLineAmountWithoutTax -= amt_without_tax
                        totalTaxAmount -= tax_amt
                        totalAmountWithoutTax -= amt_without_tax
                        totalAmountWithTax -= amt_with_tax
                        totalDiscountAmount += amt_without_tax
                    else:
                        sumOfTotalLineAmountWithoutTax += amt_without_tax
                        totalTaxAmount += tax_amt
                        totalAmountWithoutTax += amt_without_tax
                        totalAmountWithTax += amt_with_tax
            summarizeInfo = {
                "sumOfTotalLineAmountWithoutTax": sumOfTotalLineAmountWithoutTax,
                "totalTaxAmount": totalTaxAmount,
                "totalAmountWithoutTax": totalAmountWithoutTax,
                "totalAmountWithTax": totalAmountWithTax,
                "discountAmount": totalDiscountAmount,
            }
        return summarizeInfo
    
    def get_breakdown(self):
        breakdown = {}
        has_mixed_types = self._check_has_mixed_item_types()
        for invoice_line in self.sinvoice_data_ids:
            if len(invoice_line.tax_ids):
                # Xác định dấu: trừ cho dòng chiết khấu trong hóa đơn hỗn hợp
                is_discount_in_mixed = has_mixed_types and invoice_line.vsi_item_type == 'chiet_khau'
                sign = -1 if is_discount_in_mixed else 1
                subtotal = abs(invoice_line.price_subtotal)
                for tax_id in invoice_line.tax_ids:
                    if tax_id.id not in breakdown:
                        if tax_id.not_taxable:
                            taxPercentage = -2
                        elif tax_id.not_declared_paid:
                            taxPercentage = -1
                        else:
                            taxPercentage = tax_id.amount

                        breakdown[tax_id.id] = {
                            "taxPercentage": taxPercentage,
                            "taxableAmount": sign * subtotal,
                            "taxAmount": sign * subtotal * tax_id.amount / 100,
                        }
                    else:
                        breakdown[tax_id.id]["taxableAmount"] += sign * subtotal
                        breakdown[tax_id.id]["taxAmount"] += sign * (subtotal * tax_id.amount / 100)
                    break
        return breakdown
    
    def get_generalInvoiceInfo(self, invoiceIssuedDate=False):
        if not invoiceIssuedDate:
            invoiceIssuedDate = self.invoiceIssuedDate
        code = self.vsi_type_code
        if not code:
            raise UserError('Please config `Invoice Type` for your company!')
            return False
        invoiceIssuedDate_str = str(invoiceIssuedDate.strftime("%Y-%m-%d %H:%M:%S"))
        invoiceIssuedDate_int = int(datetime.strptime(invoiceIssuedDate_str, "%Y-%m-%d %H:%M:%S").timestamp())
        generalInvoiceInfo = {
            "transactionUuid": "%s"%( uuid.uuid1()),
            "userName": self.user_id.name,
            "currencyCode": self.currency_id.name,
            "invoiceIssuedDate": invoiceIssuedDate_int * 1000,
            "invoiceSignedDate": invoiceIssuedDate_int * 1000,
            "templateCode": self.config_id.vsi_template,  # config
            "invoiceSeries": self.config_id.vsi_series,  # config
            "invoiceType": code,  # config
            "paymentType": "TM/CK",
            "paymentTypeName": "TM/CK",
            "paymentStatus": True,
            "adjustmentType":1,
        }
        return generalInvoiceInfo
    
    def get_buyerInfo(self):
        buyerInfo = {
            "buyerAddressLine": "%s" % (self.partner_vat_address),
            'buyerCode': self.partner_vat_id.ref or '',
            'buyerName': self.partner_vat_name or '',
            "buyerLegalName": self.partner_vat_id.name or ''
        }
        if self.partner_vat_id.email:
            buyerInfo.update({"buyerEmail": self.partner_vat_id.email})

        if self.partner_vat:
            buyerInfo.update({"buyerTaxCode": self.partner_vat})
            
        if self.partner_vat_id.phone:
            buyerInfo.update({"buyerPhoneNumber": self.partner_vat_id.phone})

        return buyerInfo
    
    def get_payments(self):
        return [{
            "paymentMethodName": "TM/CK",
        }]
        
    def create_data_sinvoice_line(self, line, sinvoice_edit_type=False, edit_type=False, sale_line_id=False):
        self.ensure_one()
        results = []
        name = line.name or line.product_id.name
        if line.price_unit == 0:
            name += _('- no charge')
        if line.display_type != False:
            if _('- no charge') in name:
                name = name.replace(_('- no charge'), '')
        price_unit = line.price_unit
        if sale_line_id:
            price_unit = sale_line_id.price_unit
        vals = {
                'name': name,
                'origin': name,
                'account_id': line.account_id.id,
                'price_unit': price_unit,
                'quantity': line.quantity,
                'discount': line.discount,
                'product_uom_id': line.product_uom_id.id,
                'product_id': line.product_id.id or False,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
                'sinvoice_id': self.id,
                'vsi_item_type': self._get_default_item_type_for_line(line),
            }
        if sinvoice_edit_type and sinvoice_edit_type == 'amount':
            vals['edit_type'] = edit_type
        if line.display_type == 'line_section':
            vals['display_type'] = line.display_type
        if line.display_type == 'line_note':
            vals['display_type'] = line.display_type
        results.append(vals)
        return results

    def action_get_preview_pdf(self):
        attachment_id = False
        invoiceIssuedDate = datetime.now()
        config_id = self.config_id
        self = self.with_context(lang=self.env.user.lang)
        try:
            if not config_id:
                raise ValidationError(_('Please select viettel config'))

            api_url = '/services/einvoiceapplication/api/InvoiceAPI/InvoiceUtilsWS/createInvoiceDraftPreview/' + config_id.vsi_tin
            if not self.partner_vat_id:
                raise UserError(_("Please select an invoice customer"))
            
            data = self.get_post_data_sinvoice(invoiceIssuedDate)
            headers = {
                'Content-Type': 'application/json'
            }
            response = config_id.execute_request(self ,"POST", api_url, headers=headers, data=data)
            if response.get('success', False):
                data = response['data']
                fileToBytes = data.get('fileToBytes')
                filename = "%s_preview.pdf" % self.id
                attachment_id = self.env['ir.attachment'].search([('res_model','=','viettel.sinvoice'),('res_id','=',self.id),('name','=',filename)],limit=1)
                if not attachment_id:
                    attachment = {
                        'name': filename,
                        'datas': fileToBytes,
                        'res_model': 'viettel.sinvoice',
                        'res_id': self.id,
                    }
                    attachment_id = self.env['ir.attachment'].create(attachment)
                else:
                    attachment_id.write({
                        'datas': fileToBytes,
                    })
            else:
                return {
                    'success': False,
                    'error': response['error']
                }

        except Exception as e:
            return {
                'success': False,
                'error': e
            }

        return {
            'success': True,
            'attachment': attachment_id and attachment_id.id or False    
        }