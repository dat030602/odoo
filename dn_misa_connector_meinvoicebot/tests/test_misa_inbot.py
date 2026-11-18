# -*- coding: utf-8 -*-
import sys
import os
import json
import base64
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Ensure odoo and custom addons are on Python path if running standalone
if '/opt/odoo19' not in sys.path:
    sys.path.insert(0, '/opt/odoo19')

import odoo
import odoo.addons
addons_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if hasattr(odoo.addons, '__path__') and addons_dir not in odoo.addons.__path__:
    odoo.addons.__path__.append(addons_dir)

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.dn_misa_connector_meinvoicebot.models.misa_inbot_document import MisaInbotDocument
from odoo.addons.dn_misa_connector_meinvoicebot.models.misa_inbot_document_line import MisaInbotDocumentLine
from odoo.addons.dn_misa_connector_meinvoicebot.models.misa_inbot_zip_downloader import MisaInbotZipDownloader
from odoo.addons.dn_misa_connector_meinvoicebot.wizard.misa_inbot_sync_wizard import MisaInbotSyncWizard


@tagged('post_install', '-at_install')
class TestMisaInbot(unittest.TestCase):
    """Unit tests for dn_misa_connector_meinvoicebot logic and features."""

    def setUp(self):
        super().setUp()

    # -------------------------------------------------------------------------
    # 1. Test Seller Risk Status (Rủi ro người bán)
    # -------------------------------------------------------------------------
    def test_01_seller_risk_status_blacklist_tax_blocked(self):
        """Seller with status '2' (Blacklist thuế) raises UserError blocking account.move creation."""
        mock_doc = MagicMock(spec=MisaInbotDocument)
        mock_doc.ensure_one.return_value = True
        mock_doc.move_id = False
        mock_doc.is_inbot = True
        mock_doc.seller_risk_status = '2'
        mock_doc.seller_name = "Công ty Ma Lừa Đảo"
        mock_doc.seller_tax_code = "0109999999"
        mock_field_seller_risk = MagicMock()
        mock_field_seller_risk.selection = [
            ('1', '1 - Bình thường (No Risk)'),
            ('2', '2 - Rủi ro danh sách đen thuế (Blacklisted)'),
            ('3', '3 - Chưa đủ thông tin kết luận'),
            ('4', '4 - Ngừng HĐ tại địa chỉ đăng ký (Inactive address)'),
        ]
        mock_doc._fields = {'seller_risk_status': mock_field_seller_risk}

        with self.assertRaises(UserError) as cm:
            MisaInbotDocument.action_create_account_move(mock_doc)
        self.assertIn("flagged with high tax risk", str(cm.exception))

    def test_02_seller_risk_status_inactive_address_blocked(self):
        """Seller with status '4' (Ngừng HĐ tại địa chỉ ĐKKD) raises UserError blocking account.move creation."""
        mock_doc = MagicMock(spec=MisaInbotDocument)
        mock_doc.ensure_one.return_value = True
        mock_doc.move_id = False
        mock_doc.is_inbot = True
        mock_doc.seller_risk_status = '4'
        mock_doc.seller_name = "Công ty Bỏ Trốn"
        mock_doc.seller_tax_code = "0108888888"
        mock_field_seller_risk = MagicMock()
        mock_field_seller_risk.selection = [
            ('1', '1 - Bình thường (No Risk)'),
            ('2', '2 - Rủi ro danh sách đen thuế (Blacklisted)'),
            ('3', '3 - Chưa đủ thông tin kết luận'),
            ('4', '4 - Ngừng HĐ tại địa chỉ đăng ký (Inactive address)'),
        ]
        mock_doc._fields = {'seller_risk_status': mock_field_seller_risk}

        with self.assertRaises(UserError) as cm:
            MisaInbotDocument.action_create_account_move(mock_doc)
        self.assertIn("flagged with high tax risk", str(cm.exception))

    def test_03_seller_risk_status_normal_allowed(self):
        """Seller with status '1' (Bình thường) allows creating account.move."""
        mock_doc = MagicMock(spec=MisaInbotDocument)
        mock_doc.ensure_one.return_value = True
        mock_doc.move_id = False
        mock_doc.is_inbot = True
        mock_doc.seller_risk_status = '1'
        mock_doc.seller_name = "Công ty TNHH Hợp Lệ"
        mock_doc.seller_tax_code = "0101234567"
        mock_doc.seller_address = "Hà Nội"
        mock_doc.invoice_no = "INV-001"
        mock_doc.name = "[IN] C25T #INV-001"
        mock_doc.invoice_date = fields.Date.today()
        mock_doc.currency_id.id = 1
        mock_doc.company_id.id = 1
        mock_doc.id = 99
        mock_doc.t_thai_xu_ly = '0'
        mock_doc.fee_line_ids = []
        mock_doc._attach_files_to_move = MagicMock()
        mock_field_seller_risk = MagicMock()
        mock_field_seller_risk.selection = [
            ('1', '1 - Bình thường (No Risk)'),
            ('2', '2 - Rủi ro danh sách đen thuế (Blacklisted)'),
            ('3', '3 - Chưa đủ thông tin kết luận'),
            ('4', '4 - Ngừng HĐ tại địa chỉ đăng ký (Inactive address)'),
        ]
        mock_doc._fields = {'seller_risk_status': mock_field_seller_risk}

        # Line mock
        mock_line = MagicMock(spec=MisaInbotDocumentLine)
        mock_line.kind = '0'
        mock_line.item_name = "Dịch vụ phần mềm"
        mock_line.unit_price = 1000000.0
        mock_line.quantity = 1.0
        mock_line.discount_amount = 0.0
        mock_line.amount_without_vat = 1000000.0
        mock_doc.line_ids = [mock_line]

        # Partner and Tax resolution mocks
        mock_partner = MagicMock()
        mock_partner.id = 42
        mock_doc._find_or_create_partner.return_value = mock_partner

        mock_tax = MagicMock()
        mock_tax.ids = [10]
        mock_doc._find_tax_for_line.return_value = mock_tax

        mock_move = MagicMock()
        mock_move.id = 100
        mock_env_move = MagicMock()
        mock_env_move.create.return_value = mock_move
        mock_doc.env = MagicMock()
        mock_doc.env.lang = 'en_US'
        mock_doc.env.__getitem__.side_effect = lambda m: mock_env_move if m == 'account.move' else MagicMock()

        res = MisaInbotDocument.action_create_account_move(mock_doc)

        mock_env_move.create.assert_called_once()
        create_args = mock_env_move.create.call_args[0][0]
        self.assertEqual(create_args['move_type'], 'in_invoice')
        self.assertEqual(create_args['partner_id'], 42)
        self.assertEqual(create_args['misa_inbot_id'], 99)
        mock_doc.write.assert_called_once_with({
            'move_id': 100,
            't_thai_xu_ly': '1',
        })
        self.assertEqual(res['res_id'], 100)

    # -------------------------------------------------------------------------
    # 2. Test Quy tắc bảo vệ file XML (Anti-overwrite rule for source_type == '1')
    # -------------------------------------------------------------------------
    def test_04_protect_original_xml_in_sync_wizard(self):
        """When source_type == '1' (User uploaded XML), sync payload must not overwrite xml_file."""
        mock_wizard = MagicMock(spec=MisaInbotSyncWizard)
        mock_wizard.ensure_one.return_value = True
        mock_wizard.take = 50
        mock_wizard.skip = 0
        mock_wizard.from_date = datetime(2026, 1, 1).date()
        mock_wizard.to_date = datetime(2026, 1, 31).date()
        mock_wizard.is_filter_inv_date = False
        mock_wizard.invoice_direction = 'in_invoice'
        mock_wizard.organization_id.subscriber_id = 'SUB001'
        mock_wizard.organization_id.org_id = 'ORG001'
        mock_wizard.company_id.id = 1

        mock_doc = MagicMock(spec=MisaInbotDocument)
        mock_doc.source_type = '1'
        mock_doc.xml_file = base64.b64encode(b"<OriginalUserXml/>")
        mock_doc.xml_filename = "original_user.xml"

        mock_doc_obj = MagicMock()
        mock_doc_obj.search.return_value = mock_doc
        mock_wizard.env = MagicMock()
        mock_wizard.env.lang = 'en_US'
        mock_wizard.env.__getitem__.side_effect = lambda m: mock_doc_obj if m == 'misa.inbot.document' else MagicMock()

        # Simulated incoming payload from MISA sync containing new XML
        api_data = {
            'is_success': True,
            'data': [{
                'InvoiceId': 'INV-12345',
                'TypeInvoiceReceive': 0,  # sync source
                'InvoiceNo': '0000001',
                'Series': '1C25TYY',
                'SellerName': 'Supplier A',
                'SellerTaxCode': '0101111111',
            }]
        }
        mock_wizard.company_id._execute_inbot_api.return_value = api_data

        with patch.object(MisaInbotSyncWizard, '_prepare_document_vals') as mock_prep, \
             patch.object(MisaInbotSyncWizard, '_sync_document_details'):
            # Prepare returns vals that might include xml_file
            mock_prep.return_value = {
                'invoice_no': '0000001',
                'xml_file': base64.b64encode(b"<NewApiXml/>"),
                'xml_filename': 'api_sync.xml',
            }
            MisaInbotSyncWizard.action_sync_invoices(mock_wizard)

            # Check that doc.write was called WITHOUT xml_file and xml_filename
            mock_doc.write.assert_called_once()
            written_vals = mock_doc.write.call_args[0][0]
            self.assertNotIn('xml_file', written_vals, "Original xml_file must not be overwritten when source_type == '1'")
            self.assertNotIn('xml_filename', written_vals, "Original xml_filename must not be overwritten when source_type == '1'")

    def test_05_protect_original_xml_in_zip_downloader(self):
        """When source_type == '1', zip downloader _match_and_attach_file does not overwrite xml_file."""
        mock_task = MagicMock(spec=MisaInbotZipDownloader)
        mock_task.company_id.id = 1
        mock_task.invoice_ids = json.dumps(['INV-12345'])

        mock_doc = MagicMock(spec=MisaInbotDocument)
        mock_doc.source_type = '1'

        mock_doc_obj = MagicMock()
        mock_doc_obj.search.return_value = mock_doc
        mock_task.env = MagicMock()
        mock_task.env.lang = 'en_US'
        mock_task.env.__getitem__.side_effect = lambda m: mock_doc_obj if m == 'misa.inbot.document' else MagicMock()

        # Attempt to attach an XML file for this document
        MisaInbotZipDownloader._match_and_attach_file(
            mock_task, "INV-12345.xml", base64.b64encode(b"<ZipXmlContent/>")
        )
        # write should NOT be called on mock_doc because xml_file was blocked
        mock_doc.write.assert_not_called()

        # If source_type != '1', XML should be written
        mock_doc.source_type = '0'
        MisaInbotZipDownloader._match_and_attach_file(
            mock_task, "INV-12345.xml", base64.b64encode(b"<ZipXmlContent/>")
        )
        mock_doc.write.assert_called_once_with({
            'xml_file': base64.b64encode(b"<ZipXmlContent/>"),
            'xml_filename': "INV-12345.xml",
        })

    # -------------------------------------------------------------------------
    # 3. Test Tính toán độ trễ hàng đợi tải ZIP (misa.inbot.zip.downloader)
    # -------------------------------------------------------------------------
    def test_06_zip_downloader_delay_minimum_15s(self):
        """For 1 invoice, delay = max(15, 1 * 10) = 15 seconds."""
        mock_task = MagicMock(spec=MisaInbotZipDownloader)
        mock_task.ensure_one.return_value = True
        mock_task.subscriber_id = "SUB001"
        mock_task.org_id = "ORG001"
        mock_task.file_type = '1'
        mock_task.is_inbot = True
        mock_task.invoice_ids = json.dumps(['INV-01'])
        mock_task.company_id._execute_inbot_api.return_value = {
            'is_success': True,
            'data': {'Key': 'DOWNLOAD_KEY_123'},
        }

        fixed_now = datetime(2026, 11, 18, 10, 0, 0)
        with patch('odoo.fields.Datetime.now', return_value=fixed_now):
            MisaInbotZipDownloader.action_request_zip_key(mock_task)

            mock_task.write.assert_called_once()
            vals = mock_task.write.call_args[0][0]
            self.assertEqual(vals['download_key'], 'DOWNLOAD_KEY_123')
            self.assertEqual(vals['invoice_count'], 1)
            # max(15, 1 * 10) = 15s delay
            expected_sched = fixed_now + timedelta(seconds=15)
            self.assertEqual(vals['scheduled_time'], expected_sched)
            self.assertEqual(vals['state'], 'scheduled')

    def test_07_zip_downloader_delay_scaled_by_count(self):
        """For 5 invoices, delay = max(15, 5 * 10) = 50 seconds."""
        mock_task = MagicMock(spec=MisaInbotZipDownloader)
        mock_task.ensure_one.return_value = True
        mock_task.subscriber_id = "SUB001"
        mock_task.org_id = "ORG001"
        mock_task.file_type = '1'
        mock_task.is_inbot = True
        mock_task.invoice_ids = json.dumps(['INV-01', 'INV-02', 'INV-03', 'INV-04', 'INV-05'])
        mock_task.company_id._execute_inbot_api.return_value = {
            'is_success': True,
            'data': {'Key': 'KEY_5_ITEMS'},
        }

        fixed_now = datetime(2026, 11, 18, 10, 0, 0)
        with patch('odoo.fields.Datetime.now', return_value=fixed_now):
            MisaInbotZipDownloader.action_request_zip_key(mock_task)

            mock_task.write.assert_called_once()
            vals = mock_task.write.call_args[0][0]
            self.assertEqual(vals['invoice_count'], 5)
            # max(15, 5 * 10) = 50s delay
            expected_sched = fixed_now + timedelta(seconds=50)
            self.assertEqual(vals['scheduled_time'], expected_sched)

    # -------------------------------------------------------------------------
    # 4. Test Mapping trường Nghị định 70 (header và lines)
    # -------------------------------------------------------------------------
    def test_08_decree_70_header_and_lines_mapping(self):
        """Check mapping of Decree 70 fields on decoupled document and document line models."""
        mock_wizard = MagicMock(spec=MisaInbotSyncWizard)
        mock_wizard.company_id.id = 1

        payload_item = {
            'InvoiceId': 'INV-ND70-001',
            'TypeInvoiceReceive': 0,
            'InvoiceNo': '0000099',
            'Series': '1C25TND',
            'BuyerMSDVCQHVNS': 'MSD-BUYER-01',
            'SellerMSDVCQHVNS': 'MSD-SELLER-01',
            'BuyerNoCitizenIdentityCard': '001090000123',
            'BuyerPassportNumber': 'B1234567',
            'NumberAgreement': 'HD-2026-70',
            'AgreementDate': '2026-01-15',
            'LicensePlate': '29A-999.99',
            'From': 'Kho Hà Nội',
            'Destination': 'Kho Hải Phòng',
            'IsReceiptDecree70': True,
            'IsDiscountDecree70': False,
            'Items': [{
                'ItemId': 'CAR-001',
                'LineNumber': 1,
                'ItemName': 'Ô tô VinFast VF8',
                'Quantity': 1.0,
                'UnitPrice': 1000000000.0,
                'AmountWithoutVat': 1000000000.0,
                'VatRate': '10',
                'VatAmount': 100000000.0,
                'Amount': 1100000000.0,
                'SpecificProductType': '1',
                'VehicleFrameNumber': 'VF8FRAME123456789',
                'VehicleEngineNumber': 'VF8ENG987654321',
                'TransportLicensePlate': '29C-888.88',
                'ShipperName': 'Nguyễn Văn Vận Chuyển',
                'ShipperAddress': 'Số 1 Mai Dịch, Hà Nội',
                'ShipperTaxCode': '0102223334',
                'ShipperIdentifier': '001088000456',
            }]
        }

        # 1. Check Header vals preparation
        vals = MisaInbotSyncWizard._prepare_document_vals(
            mock_wizard, payload_item, 'SUB-01', 'ORG-01', is_inbot=True
        )
        self.assertEqual(vals['buyer_msdvcqhvns'], 'MSD-BUYER-01')
        self.assertEqual(vals['seller_msdvcqhvns'], 'MSD-SELLER-01')
        self.assertEqual(vals['buyer_no_citizen_identity_card'], '001090000123')
        self.assertEqual(vals['buyer_passport_number'], 'B1234567')
        self.assertEqual(vals['number_agreement'], 'HD-2026-70')
        self.assertEqual(vals['agreement_date'], datetime(2026, 1, 15).date())
        self.assertEqual(vals['license_plate'], '29A-999.99')
        self.assertEqual(vals['from_location'], 'Kho Hà Nội')
        self.assertEqual(vals['destination'], 'Kho Hải Phòng')
        self.assertTrue(vals['is_receipt_decree70'])
        self.assertFalse(vals['is_discount_decree70'])

        # 2. Check Line sync mapping
        mock_doc = MagicMock(spec=MisaInbotDocument)
        mock_doc.line_ids = MagicMock()
        mock_doc.related_line_ids = MagicMock()
        mock_doc.fee_line_ids = MagicMock()

        MisaInbotSyncWizard._sync_document_details(mock_wizard, mock_doc, payload_item)

        # Ensure old lines were unlinked
        mock_doc.line_ids.unlink.assert_called_once()
        # Ensure new lines were created with Decree 70 fields
        mock_doc.write.assert_called_once()
        lines_written = mock_doc.write.call_args[0][0].get('line_ids')
        self.assertTrue(lines_written)
        line_data = lines_written[0][2]
        self.assertEqual(line_data['item_id'], 'CAR-001')
        self.assertEqual(line_data['specific_product_type'], '1')
        self.assertEqual(line_data['vehicle_frame_number'], 'VF8FRAME123456789')
        self.assertEqual(line_data['vehicle_engine_number'], 'VF8ENG987654321')
        self.assertEqual(line_data['transport_license_plate'], '29C-888.88')
        self.assertEqual(line_data['shipper_name'], 'Nguyễn Văn Vận Chuyển')
        self.assertEqual(line_data['shipper_address'], 'Số 1 Mai Dịch, Hà Nội')
        self.assertEqual(line_data['shipper_tax_code'], '0102223334')
        self.assertEqual(line_data['shipper_identifier'], '001088000456')

    # -------------------------------------------------------------------------
    # 5. Test Đồng bộ 2 chiều: Accounting Date (action_sync_accounting_date)
    # -------------------------------------------------------------------------
    def test_09_action_sync_accounting_date_payload(self):
        """action_sync_accounting_date generates correct payload format (Accountant, AccountingDate, InvoiceId, RefNo)."""
        mock_doc = MagicMock(spec=MisaInbotDocument)
        mock_doc.invoice_id = 'INV-9999'
        mock_doc.subscriber_id = 'SUB-TEST'
        mock_doc.org_id = 'ORG-TEST'
        mock_doc.company_id.name = 'Test Company'
        mock_doc.company_id._execute_inbot_api.return_value = {'is_success': True}
        mock_doc.__iter__.return_value = [mock_doc]
        mock_doc.message_post = MagicMock()

        # Account move mock
        mock_move = MagicMock()
        mock_move.name = 'BILL/2026/0001'
        mock_move.date = datetime(2026, 11, 20).date()
        mock_doc.move_id = mock_move

        # User mock for accountant
        mock_user = MagicMock()
        mock_user.name = 'Kế Toán Viên A'
        mock_doc.env.user = mock_user

        MisaInbotDocument.action_sync_accounting_date(mock_doc, move=mock_move)

        mock_doc.company_id._execute_inbot_api.assert_called_once()
        args, kwargs = mock_doc.company_id._execute_inbot_api.call_args
        endpoint = args[0]
        json_data = kwargs.get('json_data')

        self.assertEqual(endpoint, 'meinvoicebot/v1/SUB-TEST/ORG-TEST/invoices/invoiceaccountingdateV2')
        self.assertEqual(json_data['Accountant'], 'Kế Toán Viên A')
        self.assertEqual(json_data['AccountingDate'], '2026-11-20')
        self.assertEqual(json_data['InvoiceId'], 'INV-9999')
        self.assertEqual(json_data['RefNo'], 'BILL/2026/0001')
        self.assertEqual(mock_doc.t_thai_xu_ly, '3')
        mock_doc.message_post.assert_called_once()

    # -------------------------------------------------------------------------
    # 6. Test Đồng bộ 2 chiều: Payment Status (action_sync_payment_status)
    # -------------------------------------------------------------------------
    def test_10_action_sync_payment_status_paid(self):
        """When residual is 0 and paid > 0, AmountPayment code is 2 (Fully Paid)."""
        mock_doc = MagicMock(spec=MisaInbotDocument)
        mock_doc.invoice_id = 'INV-PAY-01'
        mock_doc.subscriber_id = 'SUB-TEST'
        mock_doc.org_id = 'ORG-TEST'
        mock_doc.total_amount = 5000000.0
        mock_doc.company_id._execute_inbot_api.return_value = {'is_success': True}
        mock_doc.__iter__.return_value = [mock_doc]
        mock_doc.message_post = MagicMock()

        mock_move = MagicMock()
        mock_move.amount_total = 5000000.0
        mock_move.amount_residual = 0.0  # Fully paid
        mock_doc.move_id = mock_move

        fixed_today = datetime(2026, 11, 18).date()
        with patch('odoo.fields.Date.today', return_value=fixed_today):
            MisaInbotDocument.action_sync_payment_status(mock_doc, move=mock_move)

            args, kwargs = mock_doc.company_id._execute_inbot_api.call_args
            json_data = kwargs.get('json_data')

            self.assertEqual(json_data['InvoiceId'], 'INV-PAY-01')
            self.assertEqual(json_data['PaymentDate'], '2026/11/18')
            self.assertEqual(json_data['AmountPayment'], 2)  # 2: Fully paid
            self.assertEqual(json_data['PaymentPair'], 5000000.0)
            self.assertEqual(json_data['TotalAmountPayment'], 5000000.0)
            self.assertEqual(json_data['TotalAmountNotPayment'], 0.0)
            self.assertEqual(mock_doc.t_thai_xu_ly, '4')
            mock_doc.message_post.assert_called_once()

    def test_11_action_sync_payment_status_partial(self):
        """When 0 < residual < total_amount, AmountPayment code is 5 (Partially Paid)."""
        mock_doc = MagicMock(spec=MisaInbotDocument)
        mock_doc.invoice_id = 'INV-PAY-02'
        mock_doc.subscriber_id = 'SUB-TEST'
        mock_doc.org_id = 'ORG-TEST'
        mock_doc.total_amount = 10000000.0
        mock_doc.company_id._execute_inbot_api.return_value = {'is_success': True}
        mock_doc.__iter__.return_value = [mock_doc]
        mock_doc.message_post = MagicMock()

        mock_move = MagicMock()
        mock_move.amount_total = 10000000.0
        mock_move.amount_residual = 4000000.0  # 6,000,000 paid, 4,000,000 remaining
        mock_doc.move_id = mock_move

        MisaInbotDocument.action_sync_payment_status(mock_doc, move=mock_move)

        args, kwargs = mock_doc.company_id._execute_inbot_api.call_args
        json_data = kwargs.get('json_data')

        self.assertEqual(json_data['InvoiceId'], 'INV-PAY-02')
        self.assertEqual(json_data['AmountPayment'], 5)  # 5: Partially paid
        self.assertEqual(json_data['PaymentPair'], 6000000.0)
        self.assertEqual(json_data['TotalAmountPayment'], 6000000.0)
        self.assertEqual(json_data['TotalAmountNotPayment'], 4000000.0)
        mock_doc.message_post.assert_called_once()

    def test_12_action_sync_payment_status_not_paid(self):
        """When residual == total_amount (paid == 0), AmountPayment code is 1 (Not Paid)."""
        mock_doc = MagicMock(spec=MisaInbotDocument)
        mock_doc.invoice_id = 'INV-PAY-03'
        mock_doc.subscriber_id = 'SUB-TEST'
        mock_doc.org_id = 'ORG-TEST'
        mock_doc.total_amount = 8000000.0
        mock_doc.company_id._execute_inbot_api.return_value = {'is_success': True}
        mock_doc.__iter__.return_value = [mock_doc]
        mock_doc.message_post = MagicMock()

        mock_move = MagicMock()
        mock_move.amount_total = 8000000.0
        mock_move.amount_residual = 8000000.0  # Nothing paid
        mock_doc.move_id = mock_move

        MisaInbotDocument.action_sync_payment_status(mock_doc, move=mock_move)

        args, kwargs = mock_doc.company_id._execute_inbot_api.call_args
        json_data = kwargs.get('json_data')

        self.assertEqual(json_data['InvoiceId'], 'INV-PAY-03')
        self.assertEqual(json_data['AmountPayment'], 1)  # 1: Not paid
        self.assertEqual(json_data['PaymentPair'], 0.0)
        self.assertEqual(json_data['TotalAmountPayment'], 0.0)
        self.assertEqual(json_data['TotalAmountNotPayment'], 8000000.0)
        mock_doc.message_post.assert_called_once()


if __name__ == '__main__':
    unittest.main()
