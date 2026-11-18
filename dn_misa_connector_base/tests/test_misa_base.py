# -*- coding: utf-8 -*-
import sys
import os
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
from odoo.tests import tagged, TransactionCase

from odoo.addons.dn_misa_connector_base.models.misa_api_log import MisaApiLog
from odoo.addons.dn_misa_connector_base.models.misa_queue_job import (
    MisaQueueJob,
    _RATE_LIMIT_BUCKET,
)
from odoo.addons.dn_misa_connector_base.models.res_company import ResCompany


@tagged('post_install', '-at_install')
class TestMisaBase(unittest.TestCase):
    """Unit tests for dn_misa_connector_base logic and methods."""

    def setUp(self):
        super().setUp()
        # Clean rate limit bucket before each test
        _RATE_LIMIT_BUCKET.clear()
        self.queue_job_mock = MagicMock(spec=MisaQueueJob)
        self.api_log_mock = MagicMock(spec=MisaApiLog)

    # -------------------------------------------------------------------------
    # 1. Rate Limit (check_rate_limit) in misa.queue.job
    # -------------------------------------------------------------------------
    def test_01_check_rate_limit_under_limit(self):
        """Allow requests within the allowed maximum limit (e.g. 10 req/60s)."""
        for i in range(10):
            allowed, wait_sec = MisaQueueJob.check_rate_limit(
                self.queue_job_mock, key='test_auth_key', max_requests=10, window_seconds=60
            )
            self.assertTrue(allowed, f"Request {i+1} should be permitted")
            self.assertEqual(wait_sec, 0)

    def test_02_check_rate_limit_exceeded(self):
        """Block the 11th request when limit is 10 req/60s and return wait seconds."""
        for _ in range(10):
            allowed, _ = MisaQueueJob.check_rate_limit(
                self.queue_job_mock, key='test_rate_limit', max_requests=10, window_seconds=60
            )
            self.assertTrue(allowed)

        # 11th request must be rejected
        allowed, wait_sec = MisaQueueJob.check_rate_limit(
            self.queue_job_mock, key='test_rate_limit', max_requests=10, window_seconds=60
        )
        self.assertFalse(allowed, "11th request should be blocked by rate limiter")
        self.assertGreater(wait_sec, 0, "Wait time should be positive")
        self.assertLessEqual(wait_sec, 60, "Wait time should not exceed 60 seconds")

    def test_03_check_rate_limit_window_expiration(self):
        """Timestamps older than window_seconds should expire and free capacity."""
        past_time = fields.Datetime.now() - timedelta(seconds=70)

        # Inject 10 timestamps from 70 seconds ago
        _RATE_LIMIT_BUCKET['test_expiry'] = [past_time] * 10

        # Now calling check_rate_limit should purge expired timestamps and allow request
        allowed, wait_sec = MisaQueueJob.check_rate_limit(
            self.queue_job_mock, key='test_expiry', max_requests=10, window_seconds=60
        )
        self.assertTrue(allowed, "Expired timestamps must be purged to allow new request")
        self.assertEqual(wait_sec, 0)

    # -------------------------------------------------------------------------
    # 2. Batch Limits (validate_batch_limits)
    # -------------------------------------------------------------------------
    def test_04_validate_batch_limits_valid(self):
        """Batch with <= 30 invoices and <= 400 lines per invoice should pass."""
        invoices = []
        for i in range(30):
            inv = MagicMock()
            inv.name = f"INV-{i+1}"
            inv.line_ids = [MagicMock()] * 100
            invoices.append(inv)

        res = MisaQueueJob.validate_batch_limits(
            self.queue_job_mock, invoices, lines_per_invoice=400
        )
        self.assertTrue(res)

    def test_05_validate_batch_limits_exceed_invoices(self):
        """Batch with > 30 invoices should raise UserError."""
        invoices = [MagicMock() for _ in range(31)]

        with self.assertRaises(UserError) as ctx:
            MisaQueueJob.validate_batch_limits(self.queue_job_mock, invoices)
        self.assertIn("Maximum 30 invoice documents", str(ctx.exception))

    def test_06_validate_batch_limits_exceed_lines(self):
        """Invoice with > 400 lines should raise UserError."""
        inv = MagicMock()
        inv.name = "INV-EXCEED-LINES"
        inv.line_ids = [MagicMock()] * 401

        with self.assertRaises(UserError) as ctx:
            MisaQueueJob.validate_batch_limits(
                self.queue_job_mock, [inv], lines_per_invoice=400
            )
        self.assertIn("exceeds maximum allowed line items", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 3. Retry Logic & Error Mapping (_execute_job)
    # -------------------------------------------------------------------------
    def test_07_retry_logic_transient_error(self):
        """Auto-retry on 429, TooManyRequests, InvoiceDuplicated, or within max_retries."""
        job = MagicMock(spec=MisaQueueJob)
        job.ensure_one = MagicMock()
        job.name = "JOB/TEST/001"
        job.action_type = "publish_invoice"
        job.model_name = "account.move"
        job.res_id = 999
        job.retry_count = 1
        job.max_retries = 3
        job.env = {"account.move": MagicMock()}

        # Make record raise 429 TooManyRequests
        record_mock = MagicMock()
        record_mock.action_execute_queue_job.side_effect = Exception("429 Too Many Requests: Rate exceeded")
        job.env["account.move"].browse.return_value = record_mock

        # Call real unbound _execute_job method
        MisaQueueJob._execute_job(job)

        # Check that job.write was called with retry state
        write_calls = [call[0][0] for call in job.write.call_args_list]
        states_written = [c.get('state') for c in write_calls if 'state' in c]

        self.assertIn('processing', states_written)
        self.assertIn('retry', states_written)

        # Verify retry values
        last_write = write_calls[-1]
        self.assertEqual(last_write.get('state'), 'retry')
        self.assertEqual(last_write.get('retry_count'), 2)
        self.assertIn('429', last_write.get('error_message'))
        self.assertTrue(last_write.get('next_retry_time') is not None)

    def test_08_retry_logic_max_retries_exhausted(self):
        """When max_retries is reached and error is not auto-retryable, state becomes failed."""
        job = MagicMock(spec=MisaQueueJob)
        job.ensure_one = MagicMock()
        job.name = "JOB/TEST/002"
        job.action_type = "publish_invoice"
        job.model_name = "account.move"
        job.res_id = 888
        job.retry_count = 3
        job.max_retries = 3
        job.env = {"account.move": MagicMock()}

        record_mock = MagicMock()
        record_mock.action_execute_queue_job.side_effect = Exception("Invalid customer tax code syntax")
        job.env["account.move"].browse.return_value = record_mock

        MisaQueueJob._execute_job(job)

        write_calls = [call[0][0] for call in job.write.call_args_list]
        last_write = write_calls[-1]

        self.assertEqual(last_write.get('state'), 'failed')
        self.assertIn("Invalid customer tax code", last_write.get('error_message'))

    # -------------------------------------------------------------------------
    # 4. Sensitive Data Masking (_mask_sensitive_data) in misa.api.log
    # -------------------------------------------------------------------------
    def test_09_mask_sensitive_data(self):
        """Ensure password, PassWord, ClientSecret, client_secret, securetoken, Authorization Bearer are masked."""
        test_payload = (
            '{"taxcode": "0101234567", "username": "admin@example.com", "password": "SecretPassword123", '
            '"PassWord": "MyPassword456", "ClientSecret": "top-secret-key-abc", '
            '"client_secret": "my-client-secret-xyz", "securetoken": "jwt.sec.tok.123", '
            '"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token"}'
        )

        masked = MisaApiLog._mask_sensitive_data(self.api_log_mock, test_payload)

        self.assertNotIn("SecretPassword123", masked)
        self.assertNotIn("MyPassword456", masked)
        self.assertNotIn("top-secret-key-abc", masked)
        self.assertNotIn("my-client-secret-xyz", masked)
        self.assertNotIn("jwt.sec.tok.123", masked)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token", masked)

        self.assertIn('"password": "***"', masked)
        self.assertIn('"PassWord": "***"', masked)
        self.assertIn('"ClientSecret": "***"', masked)
        self.assertIn('"client_secret": "***"', masked)
        self.assertIn('"securetoken": "***"', masked)
        self.assertIn('"Authorization": "Bearer ***"', masked)

    def test_10_mask_sensitive_data_none_or_empty(self):
        """Handling of None or empty string values in _mask_sensitive_data."""
        self.assertIsNone(MisaApiLog._mask_sensitive_data(self.api_log_mock, None))
        self.assertEqual(MisaApiLog._mask_sensitive_data(self.api_log_mock, ""), "")

    # -------------------------------------------------------------------------
    # 5. Token Parsing and Caching Logic
    # -------------------------------------------------------------------------
    def test_11_meinvoice_token_parsing_and_caching(self):
        """Test meInvoice token retrieval, 2FA detection, and caching."""
        company = MagicMock(spec=ResCompany)
        company.ensure_one = MagicMock()
        company.name = "Test MISA Company"
        company.misa_client_id = "CID_001"
        company.misa_client_secret = "CSEC_001"
        company.misa_tax_code = "0100109106"
        company.misa_username = "test_user"
        company.misa_password = "test_password"
        company.misa_meinvoice_token = False
        company.misa_meinvoice_token_draft = False
        company.misa_meinvoice_token_expiry = False

        # Mock API returning successful token response
        token_response = {
            'is_success': True,
            'status_code': 200,
            'data': {
                'Success': True,
                'Data': 'meinvoice_access_token_mock_xyz123',
                'CustomData': {'Id': 'misa_user_uuid_001'}
            },
            'error_code': None,
            'error_message': None,
        }
        company._misa_request = MagicMock(return_value=token_response)

        token = ResCompany.action_get_meinvoice_token(company, is_draft=False, force_refresh=True)

        self.assertEqual(token, 'meinvoice_access_token_mock_xyz123')
        self.assertEqual(company.misa_meinvoice_user_id, 'misa_user_uuid_001')
        company.write.assert_called_once()
        write_args = company.write.call_args[0][0]
        self.assertEqual(write_args.get('misa_meinvoice_token'), 'meinvoice_access_token_mock_xyz123')
        self.assertEqual(write_args.get('misa_meinvoice_token_draft'), 'meinvoice_access_token_mock_xyz123')
        self.assertIsNotNone(write_args.get('misa_meinvoice_token_expiry'))

    def test_12_inbot_two_step_token_parsing_and_caching(self):
        """Test INBOT 2-step token retrieval (validateuser -> jwttoken) and caching."""
        company = MagicMock(spec=ResCompany)
        company.ensure_one = MagicMock()
        company.name = "Test INBOT Company"
        company.misa_client_id = "INBOT_CID"
        company.misa_tax_code = "0100109106"
        company.misa_username = "inbot_user"
        company.misa_password = "inbot_password"
        company.misa_inbot_jwt_token = False
        company.misa_inbot_token_expiry = False

        # Responses for Step 1 (ValidateUser) and Step 2 (auth/jwttoken)
        resp_validate_user = {
            'is_success': True,
            'status_code': 200,
            'data': {'Success': True, 'Data': 'COMP_ID_999;sec_tok_abc_789'},
            'error_code': None,
            'error_message': None,
        }
        resp_jwt_token = {
            'is_success': True,
            'status_code': 200,
            'data': {'Success': True, 'Data': 'jwt_access_token_inbot_sample'},
            'error_code': None,
            'error_message': None,
        }

        def fake_misa_request(service_type, endpoint, **kwargs):
            if endpoint == 'meinvoicebot/v1/validateuser':
                return resp_validate_user
            elif endpoint == 'meinvoicebot/v1/auth/jwttoken':
                return resp_jwt_token
            return {'is_success': False, 'error_message': 'Unknown endpoint'}

        company._misa_request = MagicMock(side_effect=fake_misa_request)

        jwt = ResCompany.action_get_inbot_jwt_token(company, force_refresh=True)

        self.assertEqual(jwt, 'jwt_access_token_inbot_sample')
        company.write.assert_called_once()
        written = company.write.call_args[0][0]
        self.assertEqual(written.get('misa_inbot_subscribers_id'), 'COMP_ID_999')
        self.assertEqual(written.get('misa_inbot_secure_token'), 'sec_tok_abc_789')
        self.assertEqual(written.get('misa_inbot_jwt_token'), 'jwt_access_token_inbot_sample')
        self.assertIsNotNone(written.get('misa_inbot_token_expiry'))

    def test_13_inbot_token_cache_hit_no_api_call(self):
        """When cached INBOT token is still valid (>10 min), return directly without API calls."""
        company = MagicMock(spec=ResCompany)
        company.ensure_one = MagicMock()
        company.misa_inbot_jwt_token = "existing_cached_inbot_token"
        company.misa_inbot_token_expiry = fields.Datetime.now() + timedelta(hours=5)
        company._misa_request = MagicMock()

        jwt = ResCompany.action_get_inbot_jwt_token(company, force_refresh=False)

        self.assertEqual(jwt, "existing_cached_inbot_token")
        company._misa_request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
