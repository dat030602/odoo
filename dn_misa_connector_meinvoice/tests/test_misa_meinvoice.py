# -*- coding: utf-8 -*-
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure odoo and custom addons are on Python path if running standalone
if '/opt/odoo19' not in sys.path:
    sys.path.insert(0, '/opt/odoo19')

import odoo
import odoo.addons
addons_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if hasattr(odoo.addons, '__path__') and addons_dir not in odoo.addons.__path__:
    odoo.addons.__path__.append(addons_dir)

from odoo.exceptions import ValidationError, UserError
from odoo.tests import tagged

from odoo.addons.dn_misa_connector_meinvoice.models.misa_invoice_template import MisaInvoiceTemplate
from odoo.addons.dn_misa_connector_meinvoice.models.misa_einvoice_document import (
    MisaEinvoiceDocument,
    REASON_CODE_SELECTION,
)
from odoo.addons.dn_misa_connector_meinvoice.models.misa_einvoice_document_line import MisaEinvoiceDocumentLine


@tagged('post_install', '-at_install')
class TestMisaMeInvoice(unittest.TestCase):
    """Unit tests for dn_misa_connector_meinvoice logic."""

    # -------------------------------------------------------------------------
    # 1. Test logic boc tach InvSeries
    # -------------------------------------------------------------------------
    def test_01_inv_series_parsing_pos_vat(self):
        """1C25MYY -> loai 1 GTGT, ma CQT 'C', hinh thuc 'M' may tinh tien."""
        mock_rec = MagicMock(spec=MisaInvoiceTemplate)
        mock_rec.__iter__.return_value = [mock_rec]
        mock_rec.inv_series = '1C25MYY'

        MisaInvoiceTemplate._compute_series_elements(mock_rec)

        self.assertEqual(mock_rec.invoice_type, '1', "Invoice type must be 1 (VAT Invoice)")
        self.assertEqual(mock_rec.tax_authority_code_type, 'C', "Tax authority code status must be 'C'")
        self.assertEqual(mock_rec.invoice_system_type, 'M', "Invoice system type must be 'M' (Cash Register / MTT)")

    def test_02_inv_series_parsing_pxk(self):
        """6K25TYY -> loai 6 PXK, ma 'K', hinh thuc 'T' thuong."""
        mock_rec = MagicMock(spec=MisaInvoiceTemplate)
        mock_rec.__iter__.return_value = [mock_rec]
        mock_rec.inv_series = '6K25TYY'

        MisaInvoiceTemplate._compute_series_elements(mock_rec)

        self.assertEqual(mock_rec.invoice_type, '6', "Invoice type must be 6 (Internal Stock Delivery Note - PXK)")
        self.assertEqual(mock_rec.tax_authority_code_type, 'K', "Tax authority code status must be 'K' (Without code)")
        self.assertEqual(mock_rec.invoice_system_type, 'T', "Invoice system type must be 'T' (Standard)")

    def test_03_inv_series_parsing_sales(self):
        """2C25TYY -> loai 2 Ban hang, ma 'C', hinh thuc 'T' thuong."""
        mock_rec = MagicMock(spec=MisaInvoiceTemplate)
        mock_rec.__iter__.return_value = [mock_rec]
        mock_rec.inv_series = '2C25TYY'

        MisaInvoiceTemplate._compute_series_elements(mock_rec)

        self.assertEqual(mock_rec.invoice_type, '2', "Invoice type must be 2 (Sales Invoice)")
        self.assertEqual(mock_rec.tax_authority_code_type, 'C', "Tax authority code status must be 'C'")
        self.assertEqual(mock_rec.invoice_system_type, 'T', "Invoice system type must be 'T' (Standard)")

    # -------------------------------------------------------------------------
    # 2. Test logic rang buoc nguoi mua
    # -------------------------------------------------------------------------
    def test_04_buyer_legal_requirements_tax_code_missing_info(self):
        """buyer_tax_code requires buyer_legal_name and buyer_address."""
        mock_doc = MagicMock(spec=MisaEinvoiceDocument)
        mock_doc.__iter__.return_value = [mock_doc]
        mock_doc.buyer_tax_code = '0101234567'
        mock_doc.buyer_budget_code = False
        mock_doc.buyer_legal_name = False
        mock_doc.buyer_address = False

        with self.assertRaises(ValidationError):
            MisaEinvoiceDocument._check_buyer_legal_requirements(mock_doc)

        mock_doc.buyer_legal_name = 'Cong ty ABC'
        mock_doc.buyer_address = False
        with self.assertRaises(ValidationError):
            MisaEinvoiceDocument._check_buyer_legal_requirements(mock_doc)

    def test_05_buyer_legal_requirements_budget_code_missing_info(self):
        """buyer_budget_code requires buyer_legal_name and buyer_address."""
        mock_doc = MagicMock(spec=MisaEinvoiceDocument)
        mock_doc.__iter__.return_value = [mock_doc]
        mock_doc.buyer_tax_code = False
        mock_doc.buyer_budget_code = '1234567'
        mock_doc.buyer_legal_name = False
        mock_doc.buyer_address = 'Ha Noi'

        with self.assertRaises(ValidationError):
            MisaEinvoiceDocument._check_buyer_legal_requirements(mock_doc)

    def test_06_buyer_legal_requirements_valid(self):
        """buyer_tax_code with both legal name and address should pass validation."""
        mock_doc = MagicMock(spec=MisaEinvoiceDocument)
        mock_doc.__iter__.return_value = [mock_doc]
        mock_doc.buyer_tax_code = '0101234567'
        mock_doc.buyer_budget_code = False
        mock_doc.buyer_legal_name = 'Cong ty TNHH Phat Trien Cong Nghe ABC'
        mock_doc.buyer_address = 'So 10 Pho Hue, Quan Hai Ba Trung, Ha Noi'

        # Must not raise ValidationError
        try:
            MisaEinvoiceDocument._check_buyer_legal_requirements(mock_doc)
        except ValidationError:
            self.fail("_check_buyer_legal_requirements raised ValidationError unexpectedly")

    # -------------------------------------------------------------------------
    # 3. Test logic Phu luc XVII & Boc tach ky hieu goc
    # -------------------------------------------------------------------------
    def test_07_phu_luc_xvii_reason_code_validation(self):
        """reference_type = 1 (Thay the) hoac 2 (Dieu chinh) bat buoc co adjust_replace_reason_code."""
        mock_doc = MagicMock(spec=MisaEinvoiceDocument)
        mock_doc.__iter__.return_value = [mock_doc]
        mock_doc.reference_type = '1'
        mock_doc.adjust_replace_reason_code = False

        with self.assertRaises(ValidationError):
            MisaEinvoiceDocument._check_adjust_replace_reason(mock_doc)

        mock_doc.reference_type = '2'
        mock_doc.adjust_replace_reason_code = False
        with self.assertRaises(ValidationError):
            MisaEinvoiceDocument._check_adjust_replace_reason(mock_doc)

        # Valid reason code in range 1..14
        valid_reason_keys = [str(i) for i in range(1, 15)]
        selection_keys = [k for k, _ in REASON_CODE_SELECTION]
        self.assertEqual(selection_keys, valid_reason_keys, "Reason codes must span 1..14")

        mock_doc.adjust_replace_reason_code = '13'
        try:
            MisaEinvoiceDocument._check_adjust_replace_reason(mock_doc)
        except ValidationError:
            self.fail("_check_adjust_replace_reason raised ValidationError unexpectedly")

    def test_08_origin_einvoice_series_parsing(self):
        """Boc tach ky hieu goc (1C24MAA -> org_inv_template_no = '1', org_inv_series = 'C24MAA')."""
        orig_doc = MagicMock(spec=MisaEinvoiceDocument)
        orig_doc.inv_series = '1C24MAA'
        orig_doc.inv_no = '00000001'
        orig_doc.inv_date = '2024-05-10'
        orig_doc.buyer_code = 'CUST01'
        orig_doc.buyer_legal_name = 'Cong ty XYZ'
        orig_doc.buyer_tax_code = '0309876543'
        orig_doc.buyer_address = 'Quan 1, TP Ho Chi Minh'
        orig_doc.buyer_full_name = 'Nguyen Van A'
        orig_doc.buyer_phone_number = '0901234567'
        orig_doc.buyer_email = 'contact@xyz.com'

        new_doc = MagicMock(spec=MisaEinvoiceDocument)
        new_doc.origin_einvoice_id = orig_doc

        MisaEinvoiceDocument._onchange_origin_einvoice(new_doc)

        self.assertEqual(new_doc.org_invoice_type, '1')
        self.assertEqual(new_doc.org_inv_template_no, '1', "Template number should be '1'")
        self.assertEqual(new_doc.org_inv_series, 'C24MAA', "Series should be stripped to 'C24MAA'")
        self.assertEqual(new_doc.org_inv_no, '00000001')
        self.assertEqual(new_doc.buyer_tax_code, '0309876543')

    # -------------------------------------------------------------------------
    # 4. Test logic lam tron dong truoc khi cong tong
    # -------------------------------------------------------------------------
    def test_09_line_and_total_calculation_with_rounding(self):
        """Kiem tra tinh toan tong tien, chiet khau, VAT va tien quy doi voi lam tron."""
        currency_mock = MagicMock()
        currency_mock.round.side_effect = lambda val: round(val, 2)
        comp_currency_mock = MagicMock()
        comp_currency_mock.round.side_effect = lambda val: round(val, 0)

        # Mock Document
        mock_doc = MagicMock(spec=MisaEinvoiceDocument)
        mock_doc.__iter__.return_value = [mock_doc]
        mock_doc.exchange_rate = 25000.0
        mock_doc.currency_id = currency_mock
        mock_doc.company_currency_id = comp_currency_mock

        # Line 1: Goods, qty 3, unit_price 100.333, discount 10%, vat 10%
        line1 = MagicMock(spec=MisaEinvoiceDocumentLine)
        line1.__iter__.return_value = [line1]
        line1.document_id = mock_doc
        line1.currency_id = currency_mock
        line1.company_currency_id = comp_currency_mock
        line1.quantity = 3.0
        line1.unit_price = 100.333
        line1.discount_rate = 10.0
        line1.vat_rate_name = '10%'
        line1.item_type = '1'

        MisaEinvoiceDocumentLine._onchange_line_amounts(line1)

        # raw_amount_oc = 3 * 100.333 = 300.999 -> rounded 301.00
        self.assertEqual(line1.amount_oc, 301.00)
        self.assertEqual(line1.amount, 7525000.0)  # 301.00 * 25000
        # raw_disc_oc = 301.00 * 0.1 = 30.10
        self.assertEqual(line1.discount_amount_oc, 30.10)
        self.assertEqual(line1.discount_amount, 752500.0)
        # amount_without_vat_oc = 301.00 - 30.10 = 270.90
        self.assertEqual(line1.amount_without_vat_oc, 270.90)
        self.assertEqual(line1.amount_without_vat, 6772500.0)
        # raw_vat_oc = 270.90 * 0.10 = 27.09
        self.assertEqual(line1.vat_amount_oc, 27.09)
        self.assertEqual(line1.vat_amount, 677250.0)

        # Line 2: Promotional item (free of charge)
        line2 = MagicMock(spec=MisaEinvoiceDocumentLine)
        line2.__iter__.return_value = [line2]
        line2.document_id = mock_doc
        line2.currency_id = currency_mock
        line2.company_currency_id = comp_currency_mock
        line2.quantity = 1.0
        line2.unit_price = 0.0
        line2.discount_rate = 0.0
        line2.vat_rate_name = '10%'
        line2.item_type = '2'

        MisaEinvoiceDocumentLine._onchange_line_amounts(line2)
        self.assertEqual(line2.amount_oc, 0.0)
        self.assertEqual(line2.amount_without_vat_oc, 0.0)
        self.assertEqual(line2.vat_amount_oc, 0.0)

        # Line 3: Commercial discount line (ItemType = '3')
        line3 = MagicMock(spec=MisaEinvoiceDocumentLine)
        line3.item_type = '3'
        line3.amount_oc = 20.00
        line3.discount_amount_oc = 0.0
        line3.amount_without_vat_oc = 20.00
        line3.vat_amount_oc = 2.00

        mock_doc.line_ids = [line1, line2, line3]

        MisaEinvoiceDocument._compute_totals(mock_doc)

        # sale_oc: 301.00 (line1) + 0 (line2) - 20.00 (line3) = 281.00
        self.assertEqual(mock_doc.total_sale_amount_oc, 281.00)
        self.assertEqual(mock_doc.total_sale_amount, 7025000.0)
        # disc_oc: 30.10 + 20.00 = 50.10
        self.assertEqual(mock_doc.total_discount_amount_oc, 50.10)
        # without_vat_oc: 270.90 - 20.00 = 250.90
        self.assertEqual(mock_doc.total_amount_without_vat_oc, 250.90)
        self.assertEqual(mock_doc.total_amount_without_vat, 6272500.0)
        # vat_oc: 27.09 - 2.00 = 25.09
        self.assertEqual(mock_doc.total_vat_amount_oc, 25.09)
        self.assertEqual(mock_doc.total_vat_amount, 627250.0)
        # total_amount_oc: 250.90 + 25.09 = 275.99
        self.assertEqual(mock_doc.total_amount_oc, 275.99)
        self.assertEqual(mock_doc.total_amount, 6899750.0)  # 275.99 * 25000

    # -------------------------------------------------------------------------
    # 5. Test cau truc payload phat hanh HSM (SignType=2) va POS (SignType=5)
    # -------------------------------------------------------------------------
    def test_10_payload_structure_hsm(self):
        """Test payload phát hành HSM (SignType=2)."""
        mock_doc = MagicMock(spec=MisaEinvoiceDocument)
        mock_doc.ensure_one = MagicMock()
        mock_doc.ref_id = 'test-uuid-hsm-001'
        mock_doc.inv_series = '1C26TYY'
        mock_doc.inv_template_no = '1'
        mock_doc.inv_date = '2026-11-18'
        mock_doc.currency_id.name = 'VND'
        mock_doc.exchange_rate = 1.0
        mock_doc.payment_method_name = 'TM/CK'
        mock_doc.is_invoice_summary = False
        mock_doc.is_send_email = True
        mock_doc.receiver_name = 'Ke toan Truong'
        mock_doc.receiver_email = 'ketoan@company.vn'
        mock_doc.buyer_code = 'KH001'
        mock_doc.buyer_legal_name = 'Cong ty TNHH Cong Nghe So'
        mock_doc.buyer_tax_code = '0108889999'
        mock_doc.buyer_address = 'Ha Noi, Viet Nam'
        mock_doc.buyer_full_name = 'Nguyen Van B'
        mock_doc.buyer_phone_number = '0988888888'
        mock_doc.buyer_email = 'nvb@company.vn'
        mock_doc.buyer_bank_account = '1900123456789'
        mock_doc.buyer_bank_name = 'Techcombank'
        mock_doc.buyer_id_number = '001099012345'
        mock_doc.buyer_passport = ''
        mock_doc.buyer_budget_code = ''
        mock_doc.total_sale_amount_oc = 1000000.0
        mock_doc.total_sale_amount = 1000000.0
        mock_doc.total_discount_amount_oc = 0.0
        mock_doc.total_discount_amount = 0.0
        mock_doc.total_amount_without_vat_oc = 1000000.0
        mock_doc.total_amount_without_vat = 1000000.0
        mock_doc.total_vat_amount_oc = 100000.0
        mock_doc.total_vat_amount = 100000.0
        mock_doc.total_amount_oc = 1100000.0
        mock_doc.total_amount = 1100000.0
        mock_doc.total_amount_in_words = 'Một triệu một trăm nghìn đồng'
        mock_doc.reference_type = '0'
        mock_doc.picking_id = False
        mock_doc.room_no = False
        mock_doc.check_in = False
        mock_doc.period_name = False
        mock_doc.old_index = False

        # 1 detail line
        line = MagicMock()
        line.item_type = '1'
        line.item_code = 'SP01'
        line.item_name = 'Dich vu phan mem'
        line.unit_name = 'Goi'
        line.quantity = 1.0
        line.unit_price = 1000000.0
        line.amount_oc = 1000000.0
        line.amount = 1000000.0
        line.discount_rate = 0.0
        line.discount_amount_oc = 0.0
        line.discount_amount = 0.0
        line.amount_without_vat_oc = 1000000.0
        line.amount_without_vat = 1000000.0
        line.vat_rate_name = '10%'
        line.vat_amount_oc = 100000.0
        line.vat_amount = 100000.0
        line.chassis_number = ''
        line.engine_number = ''
        line.license_plate = ''
        line.lot_no = ''
        line.expiry_date = None
        mock_doc.line_ids = [line]

        tax_line = MagicMock()
        tax_line.vat_rate_name = '10%'
        tax_line.amount_without_vat_oc = 1000000.0
        tax_line.amount_without_vat = 1000000.0
        tax_line.vat_amount_oc = 100000.0
        tax_line.vat_amount = 100000.0
        mock_doc.tax_line_ids = [tax_line]

        inv_data = MisaEinvoiceDocument._build_misa_invoice_payload(mock_doc)

        self.assertEqual(inv_data['RefID'], 'test-uuid-hsm-001')
        self.assertEqual(inv_data['InvSeries'], '1C26TYY')
        self.assertEqual(inv_data['TotalAmount'], 1100000.0)
        self.assertEqual(len(inv_data['OriginalInvoiceDetail']), 1)
        self.assertEqual(inv_data['OriginalInvoiceDetail'][0]['ItemName'], 'Dich vu phan mem')
        self.assertEqual(len(inv_data['TaxRateInfo']), 1)

        # When publishing with HSM: SignType must be 2
        mock_doc.sign_type = '2'
        mock_doc.state = 'draft'
        mock_doc.company_id.misa_client_id = 'client_123'
        mock_doc.company_id.action_get_meinvoice_token.return_value = 'mock_jwt_token'
        mock_doc._build_misa_invoice_payload = MagicMock(return_value=inv_data)
        mock_doc.message_post = MagicMock()

        # Mock cert search and _misa_request
        cert_search_mock = MagicMock(return_value=[MagicMock()])
        mock_doc.env.__getitem__.return_value.search = cert_search_mock

        with patch.object(mock_doc.company_id, '_misa_request') as mock_req:
            mock_req.return_value = {
                'is_success': True,
                'data': {
                    'Success': True,
                    'Result': [{'RefID': 'test-uuid-hsm-001', 'InvoiceNo': '00000045'}]
                }
            }
            MisaEinvoiceDocument.action_publish_hsm(mock_doc)
            mock_req.assert_called_once()
            call_kwargs = mock_req.call_args[1]
            json_body = call_kwargs['json_data']
            self.assertEqual(json_body['SignType'], 2, "SignType in body must be 2 for HSM")
            self.assertEqual(json_body['InvoiceData'][0]['RefID'], 'test-uuid-hsm-001')

    def test_11_payload_structure_pos_mtt(self):
        """Test payload phát hành POS khởi tạo từ máy tính tiền (SignType=5)."""
        mock_doc = MagicMock(spec=MisaEinvoiceDocument)
        mock_doc.ensure_one = MagicMock()
        mock_doc.sign_type = '5'
        mock_doc.state = 'draft'
        mock_doc.company_id.misa_client_id = 'pos_client_456'
        mock_doc.company_id.action_get_meinvoice_token.return_value = 'mock_pos_token'
        mock_doc.message_post = MagicMock()

        mock_payload = {
            'RefID': 'pos-uuid-002',
            'InvSeries': '1C26MYY',
            'TotalAmount': 50000.0,
            'OriginalInvoiceDetail': [],
            'TaxRateInfo': [],
        }
        mock_doc._build_misa_invoice_payload = MagicMock(return_value=mock_payload)

        with patch.object(mock_doc.company_id, '_misa_request') as mock_req:
            mock_req.return_value = {
                'is_success': True,
                'data': {
                    'Success': True,
                    'Result': [{'RefID': 'pos-uuid-002', 'InvoiceNo': '00000008'}]
                }
            }
            MisaEinvoiceDocument.action_publish_hsm(mock_doc)
            mock_req.assert_called_once()
            call_kwargs = mock_req.call_args[1]
            json_body = call_kwargs['json_data']
            self.assertEqual(json_body['SignType'], 5, "SignType in body must be 5 for POS / MTT")
            self.assertEqual(json_body['InvoiceData'][0]['InvSeries'], '1C26MYY')


if __name__ == '__main__':
    unittest.main()
