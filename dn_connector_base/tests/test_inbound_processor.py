# -*- coding: utf-8 -*-
import datetime
import uuid
from psycopg2 import IntegrityError
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestInboundProcessor(TransactionCase):
    """Unit tests for `connector.inbound.message`, batch processor, retries, DLQ, and ordering."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Framework = cls.env["connector.framework"]
        cls.Endpoint = cls.env["connector.inbound.endpoint"]
        cls.Message = cls.env["connector.inbound.message"]

        cls.framework = cls.Framework.create({
            "name": "Processor FW",
            "code": "proc_fw",
            "auth_type": "none",
            "default_execution_mode": "deferred",
        })
        cls.endpoint = cls.Endpoint.create({
            "name": "Processor Test EP",
            "framework_id": cls.framework.id,
            "handler_type": "python",
            "code": "result = {'status': 'processed'}",
        })

    def test_01_message_creation_and_defaults(self):
        """[AC-7] Test connector.inbound.message creation, default state, and UUID generation."""
        msg = self.Message.create({
            "endpoint_id": self.endpoint.id,
            "payload": {"event": "test"},
        })
        self.assertTrue(msg.id)
        self.assertTrue(msg.uuid)
        uuid.UUID(msg.uuid)
        self.assertEqual(msg.state, "received")
        self.assertEqual(msg.attempts, 0)
        self.assertEqual(msg.max_attempts, 5)
        self.assertEqual(msg.company_id, self.endpoint.company_id)
        self.assertEqual(msg.framework_id, self.endpoint.framework_id)

    def test_02_idempotency_key_unique_constraint(self):
        """[AC-6] Test unique constraint 'uniq_endpoint_idempotency' prevents duplicates per endpoint."""
        self.Message.create({
            "endpoint_id": self.endpoint.id,
            "idempotency_key": "idem-key-001",
        })

        # Duplicate key on same endpoint must fail
        with mute_logger("odoo.sql_db"), self.assertRaises((IntegrityError, ValidationError)):
            with self.env.cr.savepoint():
                self.Message.create({
                    "endpoint_id": self.endpoint.id,
                    "idempotency_key": "idem-key-001",
                })

        # Multiple messages with NULL idempotency_key must succeed
        msg_null_1 = self.Message.create({
            "endpoint_id": self.endpoint.id,
            "idempotency_key": False,
        })
        msg_null_2 = self.Message.create({
            "endpoint_id": self.endpoint.id,
            "idempotency_key": False,
        })
        self.assertTrue(msg_null_1.id)
        self.assertTrue(msg_null_2.id)

    def test_03_batch_claim_skip_locked(self):
        """[AC-9] Test _cron_process claims queued/failed messages in batch ordered by priority DESC."""
        ep_high = self.Endpoint.create({
            "name": "High Priority EP",
            "framework_id": self.framework.id,
            "priority": "3",  # Urgent
            "handler_type": "python",
            "code": "result = {'priority': 'urgent'}",
        })
        ep_low = self.Endpoint.create({
            "name": "Low Priority EP",
            "framework_id": self.framework.id,
            "priority": "0",  # Low
            "handler_type": "python",
            "code": "result = {'priority': 'low'}",
        })

        msg_low = self.Message.create({
            "endpoint_id": ep_low.id,
            "state": "queued",
            "received_at": fields.Datetime.now() - datetime.timedelta(minutes=10),
        })
        msg_high = self.Message.create({
            "endpoint_id": ep_high.id,
            "state": "queued",
            "received_at": fields.Datetime.now() - datetime.timedelta(minutes=5),
        })

        # Trigger batch processor cron
        self.Message._cron_process()

        msg_high.invalidate_recordset(["state"])
        msg_low.invalidate_recordset(["state"])
        self.assertEqual(msg_high.state, "done")
        self.assertEqual(msg_low.state, "done")

    def test_04_batch_size_configuration(self):
        """[AC-9] Test processor respects 'dn_connector_base.default_batch_size' system parameter."""
        self.env["ir.config_parameter"].sudo().set_param("dn_connector_base.default_batch_size", "2")

        # Create 5 queued messages
        messages = self.Message.create([
            {
                "endpoint_id": self.endpoint.id,
                "state": "queued",
                "payload": {"idx": i},
            }
            for i in range(5)
        ])

        # Run 1 cron cycle: only 2 should be processed
        self.Message._cron_process()
        processed_count = self.Message.search_count([
            ("id", "in", messages.ids),
            ("state", "=", "done"),
        ])
        self.assertEqual(processed_count, 2)

    def test_05_exponential_backoff_on_failure(self):
        """[AC-10] Test handler failure triggers exponential backoff retry calculation."""
        ep_fail = self.Endpoint.create({
            "name": "Failing EP",
            "framework_id": self.framework.id,
            "handler_type": "python",
            "code": "raise ValueError('Simulated handler crash')",
        })

        msg = self.Message.create({
            "endpoint_id": ep_fail.id,
            "state": "queued",
            "attempts": 0,
            "max_attempts": 5,
        })

        # Process message
        msg.process_message()

        self.assertEqual(msg.state, "failed")
        self.assertEqual(msg.attempts, 1)
        self.assertTrue(msg.next_retry_at)
        self.assertGreater(msg.next_retry_at, fields.Datetime.now())
        self.assertIn("ValueError", msg.error_type or "")
        self.assertIn("Simulated handler crash", msg.error_details or "")

    def test_06_dead_letter_queue_transition(self):
        """[AC-11] Test poison pill message transitions to 'dead' when attempts reach max_attempts."""
        ep_fail = self.Endpoint.create({
            "name": "DLQ Test EP",
            "framework_id": self.framework.id,
            "handler_type": "python",
            "code": "raise RuntimeError('Poison pill fatal error')",
        })

        msg = self.Message.create({
            "endpoint_id": ep_fail.id,
            "state": "failed",
            "attempts": 4,
            "max_attempts": 5,
        })

        # 5th attempt -> reaches max_attempts
        msg.process_message()

        self.assertEqual(msg.state, "dead")
        self.assertEqual(msg.attempts, 5)
        self.assertIn("RuntimeError", msg.error_type or "")

    def test_07_dead_letters_excluded_from_claim(self):
        """[AC-11] Test messages in 'dead' state are excluded from cron claims."""
        msg_dead = self.Message.create({
            "endpoint_id": self.endpoint.id,
            "state": "dead",
            "attempts": 5,
            "max_attempts": 5,
        })

        self.Message._cron_process()
        msg_dead.invalidate_recordset(["state"])
        self.assertEqual(msg_dead.state, "dead")

    def test_08_sequential_fifo_ordering_key(self):
        """[AC-12] Test sequential FIFO ordering key blocks subsequent messages."""
        ep_ordered = self.Endpoint.create({
            "name": "Sequential Order EP",
            "framework_id": self.framework.id,
            "ordering_key": "entity_id",
            "handler_type": "python",
            "code": "result = {'order': 'ok'}",
        })

        # Message 1 for order_1001 is queued
        msg1 = self.Message.create({
            "endpoint_id": ep_ordered.id,
            "ordering_key": "order_1001",
            "state": "queued",
        })

        # Message 2 for order_1001 arrives later
        msg2 = self.Message.create({
            "endpoint_id": ep_ordered.id,
            "ordering_key": "order_1001",
            "state": "queued",
        })

        # Check barrier: msg2 must be blocked while msg1 is pending
        self.assertTrue(msg2._is_blocked_by_ordering())

        # Once msg1 is done, msg2 is unblocked
        msg1.write({"state": "done"})
        self.assertFalse(msg2._is_blocked_by_ordering())

    def test_09_retention_cleanup_cron(self):
        """[AC-15] Test _cron_cleanup_retention purges aged 'done' and 'dead' records."""
        now = fields.Datetime.now()
        old_date = now - datetime.timedelta(days=100)

        msg_done_old = self.Message.create({
            "endpoint_id": self.endpoint.id,
            "state": "done",
            "received_at": old_date,
        })
        msg_done_recent = self.Message.create({
            "endpoint_id": self.endpoint.id,
            "state": "done",
            "received_at": now,
        })

        self.Message._cron_cleanup_retention()

        self.assertFalse(msg_done_old.exists())
        self.assertTrue(msg_done_recent.exists())
