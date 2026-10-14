# -*- coding: utf-8 -*-

from odoo.tests import tagged, TransactionCase
from odoo.addons.payment.tests.common import PaymentCommon
import urllib.parse


@tagged('post_install', '-at_install')
class TestVNPayPayment(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Find or create VNPay provider
        cls.vnpay_provider = cls.env['payment.provider'].search([('code', '=', 'vnpay')], limit=1)
        if not cls.vnpay_provider:
            cls.vnpay_provider = cls.env['payment.provider'].create({
                'name': 'VNPay Test',
                'code': 'vnpay',
                'state': 'test',
                'is_published': True,
                'vnpay_tmn_code': '2QXUI4B4',
                'vnpay_hash_secret': 'RAOCTPUA20CVR0EN4555MPHAZDYGDTWD',
            })
        else:
            cls.vnpay_provider.write({
                'state': 'test',
                'vnpay_tmn_code': '2QXUI4B4',
                'vnpay_hash_secret': 'RAOCTPUA20CVR0EN4555MPHAZDYGDTWD',
            })

    def _create_vnpay_tx(self, amount=100000.0, reference=None):
        pm = self.vnpay_provider.payment_method_ids[:1]
        if not pm:
            from odoo.fields import Command
            unknown_pm = self.env.ref('payment.payment_method_unknown', raise_if_not_found=False)
            if not unknown_pm:
                unknown_pm = self.env['payment.method'].with_context(active_test=False).search([('code', '=', 'unknown')], limit=1)
            self.vnpay_provider.write({'payment_method_ids': [Command.link(unknown_pm.id)]})
            unknown_pm.write({'active': True})
            pm = unknown_pm

        tx = self.env['payment.transaction'].create({
            'amount': amount,
            'currency_id': self.env.ref('base.VND').id if self.env.ref('base.VND', raise_if_not_found=False) else self.company.currency_id.id,
            'provider_id': self.vnpay_provider.id,
            'payment_method_id': pm.id,
            'reference': reference or 'TX-VNPAY-TEST-001',
            'partner_id': self.partner.id,
        })
        return tx

    def test_01_redirect_url_generation(self):
        """ Test that VNPay transaction generates a valid redirect URL with required parameters. """
        tx = self._create_vnpay_tx(amount=200000.0, reference='TEST-VNPAY-URL-01')
        rendering_values = tx._get_specific_rendering_values({})
        
        self.assertIn('api_url', rendering_values, "Rendering values must contain api_url")
        api_url = rendering_values['api_url']
        
        # Verify URL scheme and target
        self.assertTrue(
            api_url.startswith('https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?'),
            f"Expected sandbox URL but got: {api_url}"
        )
        
        # Parse query params
        parsed_url = urllib.parse.urlparse(api_url)
        params = urllib.parse.parse_qs(parsed_url.query)
        
        self.assertEqual(params.get('vnp_Command', [''])[0], 'pay')
        self.assertEqual(params.get('vnp_Version', [''])[0], '2.1.0')
        self.assertEqual(params.get('vnp_TmnCode', [''])[0], '2QXUI4B4')
        self.assertEqual(params.get('vnp_Amount', [''])[0], '20000000')  # 200,000 * 100
        self.assertEqual(params.get('vnp_TxnRef', [''])[0], 'TEST-VNPAY-URL-01')
        self.assertTrue(params.get('vnp_SecureHash', [''])[0], "Secure hash must be present in URL")

    def test_02_hash_calculation_and_verification(self):
        """ Test HMAC-SHA512 hash calculation and signature verification in connector engine. """
        engine = self.env['connector.hash.engine']
        secret = 'RAOCTPUA20CVR0EN4555MPHAZDYGDTWD'
        
        sample_params = {
            'vnp_Amount': '10000000',
            'vnp_Command': 'pay',
            'vnp_CreateDate': '20261002153000',
            'vnp_CurrCode': 'VND',
            'vnp_IpAddr': '127.0.0.1',
            'vnp_Locale': 'vn',
            'vnp_OrderInfo': 'Payment for order',
            'vnp_OrderType': 'other',
            'vnp_ReturnUrl': 'http://localhost:8069/payment/vnpay/return',
            'vnp_TmnCode': '2QXUI4B4',
            'vnp_TxnRef': 'ORDER-123',
            'vnp_Version': '2.1.0',
        }
        
        # Build hash
        calculated_hash = engine.build_sorted_query_hash(sample_params, secret, algorithm='hmac_sha512')
        self.assertTrue(calculated_hash, "Hash should be computed successfully")
        
        # Verify valid signature
        is_valid = engine.verify_hash(
            calculated_hash, sample_params, secret, algorithm='hmac_sha512', hash_style='sorted_query'
        )
        self.assertTrue(is_valid, "Signature verification should pass with correct secret")
        
        # Verify invalid signature
        is_invalid = engine.verify_hash(
            'tampered_hash_string', sample_params, secret, algorithm='hmac_sha512', hash_style='sorted_query'
        )
        self.assertFalse(is_invalid, "Signature verification must fail with wrong hash")

    def test_03_notification_success(self):
        """ Test processing successful notification callback (code 00). """
        tx = self._create_vnpay_tx(amount=100000.0, reference='TX-VNPAY-SUCCESS-01')
        secret = self.vnpay_provider.vnpay_hash_secret
        
        notification_data = {
            'vnp_Amount': '10000000',
            'vnp_BankCode': 'NCB',
            'vnp_CardType': 'ATM',
            'vnp_OrderInfo': 'Payment for TX-VNPAY-SUCCESS-01',
            'vnp_PayDate': '20261002153500',
            'vnp_ResponseCode': '00',
            'vnp_TmnCode': '2QXUI4B4',
            'vnp_TransactionNo': '14567890',
            'vnp_TransactionStatus': '00',
            'vnp_TxnRef': tx.reference,
        }
        
        # Calculate correct signature
        engine = self.env['connector.hash.engine']
        secure_hash = engine.build_sorted_query_hash(notification_data, secret, algorithm='hmac_sha512')
        notification_data['vnp_SecureHash'] = secure_hash
        
        # Process notification
        tx._process_notification_data(notification_data)
        
        self.assertEqual(tx.state, 'done', "Transaction state must be 'done' on code 00")
        self.assertEqual(tx.provider_reference, '14567890')

    def test_04_notification_canceled(self):
        """ Test processing canceled notification callback (code 24 - Customer canceled). """
        tx = self._create_vnpay_tx(amount=100000.0, reference='TX-VNPAY-CANCEL-01')
        secret = self.vnpay_provider.vnpay_hash_secret
        
        notification_data = {
            'vnp_Amount': '10000000',
            'vnp_OrderInfo': 'Payment for TX-VNPAY-CANCEL-01',
            'vnp_ResponseCode': '24',
            'vnp_TmnCode': '2QXUI4B4',
            'vnp_TransactionNo': '0',
            'vnp_TransactionStatus': '02',
            'vnp_TxnRef': tx.reference,
        }
        
        engine = self.env['connector.hash.engine']
        secure_hash = engine.build_sorted_query_hash(notification_data, secret, algorithm='hmac_sha512')
        notification_data['vnp_SecureHash'] = secure_hash
        
        tx._process_notification_data(notification_data)
        self.assertEqual(tx.state, 'cancel', "Transaction state must be 'cancel' on code 24")

    def test_05_notification_invalid_signature(self):
        """ Test processing notification callback with invalid signature. """
        tx = self._create_vnpay_tx(amount=100000.0, reference='TX-VNPAY-FAKE-01')
        
        notification_data = {
            'vnp_Amount': '10000000',
            'vnp_OrderInfo': 'Payment for TX-VNPAY-FAKE-01',
            'vnp_ResponseCode': '00',
            'vnp_TmnCode': '2QXUI4B4',
            'vnp_TxnRef': tx.reference,
            'vnp_SecureHash': 'invalid_signature_1234567890',
        }
        
        tx._process_notification_data(notification_data)
        self.assertEqual(tx.state, 'error', "Transaction state must be 'error' when signature is invalid")
