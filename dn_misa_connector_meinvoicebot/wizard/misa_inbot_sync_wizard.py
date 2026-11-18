# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MisaInbotSyncWizard(models.TransientModel):
    _name = 'misa.inbot.sync.wizard'
    _description = 'MISA INBOT Invoice Synchronization Wizard'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    organization_id = fields.Many2one(
        'misa.organization',
        string='Organization / Branch',
        required=True,
        domain="[('company_id', '=', company_id)]"
    )
    invoice_direction = fields.Selection([
        ('in_invoice', 'Inbound (Vendor Invoices - Đầu vào)'),
        ('out_invoice', 'Outbound (Customer Invoices - Đầu ra)'),
    ], string='Invoice Type', default='in_invoice', required=True)

    from_date = fields.Date(
        string='From Date',
        required=True,
        default=lambda self: fields.Date.today() - timedelta(days=7)
    )
    to_date = fields.Date(
        string='To Date',
        required=True,
        default=lambda self: fields.Date.today()
    )
    is_filter_inv_date = fields.Boolean(
        string='Filter by Invoice Date',
        default=True,
        help='True: Filter by invoice_date. False: Filter by modified_date'
    )
    take = fields.Integer(string='Batch Size (Take)', default=50, help='Max 100 per request')
    skip = fields.Integer(string='Offset (Skip)', default=0)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            org = self.env['misa.organization'].search([('company_id', '=', self.company_id.id)], limit=1)
            self.organization_id = org.id if org else False

    def action_sync_invoices(self):
        """Pull invoices from INBOT and create/update misa.inbot.document."""
        self.ensure_one()
        if self.take > 100 or self.take <= 0:
            raise UserError(_("Batch size (take) must be between 1 and 100."))

        subscriber_id = self.organization_id.subscriber_id or self.company_id.misa_inbot_subscribers_id
        org_id = self.organization_id.org_id
        if not subscriber_id or not org_id:
            raise UserError(_("Missing Subscriber ID or Organization ID for selected organization."))

        is_inbot = (self.invoice_direction == 'in_invoice')

        # Endpoint determination
        if is_inbot:
            endpoint = f"meinvoicebot/v1/{subscriber_id}/{org_id}/invoices/v2/modified"
        else:
            endpoint = f"meinvoicebot/v1/{subscriber_id}/{org_id}/OutInvoices/modified"

        params = {
            'take': self.take,
            'skip': self.skip,
            'from': self.from_date.strftime('%Y-%m-%d'),
            'to': self.to_date.strftime('%Y-%m-%d'),
            'IsFilterInvDate': str(self.is_filter_inv_date).lower(),
        }

        res = self.company_id._execute_inbot_api(endpoint, method='GET', params=params)
        if not res.get('is_success'):
            raise UserError(_("Failed to fetch invoices from MISA INBOT: %s (%s)") % (res.get('error_message'), res.get('error_code')))

        res_data = res.get('data')
        items = []
        if isinstance(res_data, dict):
            items = res_data.get('Data') or res_data.get('Items') or []
            # Extract quota monitoring info if present
            other_info = res_data.get('Other')
            if isinstance(other_info, dict):
                self._update_company_pack_info(other_info)
        elif isinstance(res_data, list):
            items = res_data

        created_count = 0
        updated_count = 0

        doc_obj = self.env['misa.inbot.document']
        for raw_item in items:
            inv_id = str(raw_item.get('InvoiceId') or raw_item.get('InvoiceID') or raw_item.get('Id') or '')
            if not inv_id:
                continue

            # Check existing document
            doc = doc_obj.search([
                ('company_id', '=', self.company_id.id),
                ('invoice_id', '=', inv_id),
                ('is_inbot', '=', is_inbot)
            ], limit=1)

            vals = self._prepare_document_vals(raw_item, subscriber_id, org_id, is_inbot)

            if not doc:
                doc = doc_obj.create(vals)
                created_count += 1
            else:
                # Anti-overwrite rule: if doc.source_type == '1', keep existing XML/attachments
                if doc.source_type == '1':
                    vals.pop('xml_file', None)
                    vals.pop('xml_filename', None)
                doc.write(vals)
                updated_count += 1

            # Sync detailed items and related invoices
            self._sync_document_details(doc, raw_item)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Completed'),
                'message': _('Successfully synchronized INBOT invoices. Created: %d, Updated: %d') % (created_count, updated_count),
                'type': 'success',
                'sticky': False,
            }
        }

    def _prepare_document_vals(self, item, subscriber_id, org_id, is_inbot):
        """Map INBOT invoice JSON payload to misa.inbot.document values."""
        # Parse Dates
        def parse_date(date_str):
            if not date_str:
                return False
            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y'):
                try:
                    return datetime.strptime(date_str.split('.')[0], fmt).date()
                except Exception:
                    continue
            return False

        # CheckingResult extraction
        chk = item.get('CheckingResult') or {}
        if not isinstance(chk, dict):
            chk = {}

        risk_status = str(chk.get('SellerRiskStatus') or item.get('RiskStatus') or '1')
        if risk_status not in ('1', '2', '3', '4'):
            risk_status = '1'

        vals = {
            'company_id': self.company_id.id,
            'is_inbot': is_inbot,
            'trans_id': item.get('TransId') or item.get('TransactionID') or '',
            'invoice_id': str(item.get('InvoiceId') or item.get('InvoiceID') or item.get('Id') or ''),
            'subscriber_id': subscriber_id,
            'org_id': org_id,
            'source_type': str(item.get('TypeInvoiceReceive') or '0'),
            'seller_tax_code': item.get('SellerTaxCode') or '',
            'seller_name': item.get('SellerName') or '',
            'seller_address': item.get('SellerAddress') or '',
            'buyer_tax_code': item.get('BuyerTaxCode') or '',
            'buyer_name': item.get('BuyerName') or '',
            'buyer_address': item.get('BuyerAddress') or '',
            'template_no': item.get('TemplateNo') or item.get('InvTemplateNo') or '',
            'series': item.get('Series') or item.get('InvSeries') or '',
            'invoice_no': item.get('InvoiceNo') or item.get('InvNo') or '',
            'invoice_date': parse_date(item.get('InvoiceDate') or item.get('InvDate')),
            'issue_date': parse_date(item.get('IssueDate')),
            'mccqt': item.get('MCCQT') or item.get('MSo') or '',
            'payment_method': item.get('PaymentMethod') or 'TM/CK',
            'ccy_code': item.get('CcyCode') or 'VND',
            'exchange_rate': float(item.get('ExchangeRate') or 1.0),
            'total_sale_amount': float(item.get('TotalSaleAmount') or 0.0),
            'total_sale_amount_cc': float(item.get('TotalSaleAmountCC') or 0.0),
            'total_discount_amount': float(item.get('TotalDiscountAmount') or 0.0),
            'total_discount_amount_cc': float(item.get('TotalDiscountAmountCC') or 0.0),
            'total_amount_without_vat': float(item.get('TotalAmountWithoutVAT') or 0.0),
            'total_amount_without_vat_cc': float(item.get('TotalAmountWithoutVATCC') or 0.0),
            'total_vat_amount': float(item.get('TotalVATAmount') or 0.0),
            'total_vat_amount_cc': float(item.get('TotalVATAmountCC') or 0.0),
            'total_amount': float(item.get('TotalAmount') or 0.0),
            'total_amount_cc': float(item.get('TotalAmountCC') or 0.0),
            'total_tax_reduction_amount43': float(item.get('TotalTaxReductionAmount43') or 0.0),

            # Decree 70 Fields
            'buyer_msdvcqhvns': item.get('BuyerMSDVCQHVNS') or '',
            'seller_msdvcqhvns': item.get('SellerMSDVCQHVNS') or '',
            'buyer_no_citizen_identity_card': item.get('BuyerNoCitizenIdentityCard') or '',
            'buyer_passport_number': item.get('BuyerPassportNumber') or '',
            'number_agreement': item.get('NumberAgreement') or '',
            'agreement_date': parse_date(item.get('AgreementDate')),
            'license_plate': item.get('LicensePlate') or '',
            'from_location': item.get('From') or '',
            'destination': item.get('Destination') or '',
            'is_receipt_decree70': bool(item.get('IsReceiptDecree70')),
            'is_discount_decree70': bool(item.get('IsDiscountDecree70')),

            # Checking & Risk Status
            'seller_risk_status': risk_status,
            'seller_status': str(chk.get('SellerStatus') or ''),
            'buyer_status': str(chk.get('BuyerStatus') or ''),
            'published_invoice_status': str(chk.get('PublishedInvoiceStatus') or ''),
            'seller_signature_status': str(chk.get('SellerSignatureStatus') or ''),
            'taxation_signature': str(chk.get('TaxationSignature') or chk.get('TaxaxionSignature') or ''),

            # Status Flags
            'invoice_info_status_flags': str(item.get('InvoiceInfoStatusFlags') or ''),
            'checking_status_flags': str(item.get('CheckingStatusFlags') or ''),
            'tinh_chat': str(item.get('TinhChat') or '1') if str(item.get('TinhChat')) in ('1', '2', '3', '4', '5', '6') else '1',
            't_thai_hdon': str(item.get('TThaiHDon') or '1') if str(item.get('TThaiHDon')) in ('1', '2', '3', '4', '5', '6', '7') else '1',
        }
        return vals

    def _sync_document_details(self, doc, item):
        """Extract Items, InvoiceRelateds, and Fees lines into child models."""
        # 1. Items -> misa.inbot.document.line
        items = item.get('Items') or item.get('OriginalInvoiceDetail') or []
        if items and isinstance(items, list):
            doc.line_ids.unlink()
            lines = []
            for idx, it in enumerate(items, 1):
                vat_r = str(it.get('VatRate') or '10')
                if vat_r not in ('0', '5', '8', '10', '-1', '-2', '-3'):
                    vat_r = '10'

                lines.append((0, 0, {
                    'item_id': str(it.get('ItemId') or ''),
                    'line_number': int(it.get('LineNumber') or idx),
                    'item_name': it.get('ItemName') or 'Item',
                    'unit_name': it.get('UnitName') or '',
                    'quantity': float(it.get('Quantity') or 1.0),
                    'unit_price': float(it.get('UnitPrice') or 0.0),
                    'amount_without_vat': float(it.get('AmountWithoutVat') or it.get('AmountWithoutVAT') or 0.0),
                    'vat_rate': vat_r,
                    'vat_amount': float(it.get('VatAmount') or it.get('VATAmount') or 0.0),
                    'discount_amount': float(it.get('DiscountAmount') or 0.0),
                    'amount': float(it.get('Amount') or 0.0),
                    'kind': str(it.get('Kind') or '0'),
                    'specific_product_type': str(it.get('SpecificProductType') or '0'),
                    'vehicle_frame_number': it.get('VehicleFrameNumber') or '',
                    'vehicle_engine_number': it.get('VehicleEngineNumber') or '',
                    'transport_license_plate': it.get('TransportLicensePlate') or '',
                    'shipper_name': it.get('ShipperName') or '',
                    'shipper_address': it.get('ShipperAddress') or '',
                    'shipper_tax_code': it.get('ShipperTaxCode') or '',
                    'shipper_identifier': it.get('ShipperIdentifier') or '',
                }))
            doc.write({'line_ids': lines})

        # 2. InvoiceRelateds -> misa.inbot.related.line
        relateds = item.get('InvoiceRelateds') or item.get('InfoND123') or []
        if relateds and isinstance(relateds, list):
            doc.related_line_ids.unlink()
            rel_lines = []
            for r in relateds:
                rel_lines.append((0, 0, {
                    'rel_template_no': r.get('TemplateNo') or r.get('InvTemplateNo') or '',
                    'rel_series': r.get('Series') or r.get('InvSeries') or '',
                    'rel_invoice_no': r.get('InvoiceNo') or r.get('InvNo') or '',
                    'related_type': str(r.get('RelatedType') or '1'),
                }))
            doc.write({'related_line_ids': rel_lines})

        # 3. Fees -> misa.inbot.fee.line
        fees = item.get('Fees') or []
        if fees and isinstance(fees, list):
            doc.fee_line_ids.unlink()
            fee_lines = []
            for f in fees:
                fee_lines.append((0, 0, {
                    'fee_name': f.get('FeeName') or 'Fee',
                    'fee_amount': float(f.get('FeeAmount') or 0.0),
                }))
            doc.write({'fee_line_ids': fee_lines})

    def _update_company_pack_info(self, other):
        """Update company subscription and invoice quota from Other tag."""
        vals = {}
        if other.get('ProductPackCode'):
            vals['misa_inbot_product_pack_code'] = str(other.get('ProductPackCode'))
        if other.get('NumberOfInvoice') is not None:
            vals['misa_inbot_number_of_invoice'] = int(other.get('NumberOfInvoice'))
        if other.get('NumberInvUsed') is not None:
            vals['misa_inbot_number_inv_used'] = int(other.get('NumberInvUsed'))
        if other.get('NumberInvStill') is not None:
            vals['misa_inbot_number_inv_still'] = int(other.get('NumberInvStill'))
        if other.get('Status') is not None:
            vals['misa_inbot_pack_status'] = str(other.get('Status'))
        if vals:
            self.company_id.write(vals)
