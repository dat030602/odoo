# -*- coding: utf-8 -*-
from odoo.tests import tagged, TransactionCase


@tagged("post_install", "-at_install")
class TestVNAddressNQ60Connector(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Framework = cls.env["connector.framework"]
        cls.Endpoint = cls.env["connector.inbound.endpoint"]
        cls.Message = cls.env["connector.inbound.message"]
        cls.SyncService = cls.env["vn.address.nq60.connector.sync"]

        cls.framework_v2 = cls.env.ref("dn_vn_address_nq60_connector.preset_framework_vn_address_v2", raise_if_not_found=False)
        cls.endpoint_v2 = cls.env.ref("dn_vn_address_nq60_connector.endpoint_vn_address_v2", raise_if_not_found=False)

    def test_01_framework_preset_and_endpoint_v2(self):
        """Verify Open API v2 NQ60 connector framework preset and inbound endpoint exist."""
        self.assertTrue(self.framework_v2, "Framework preset vn_address_v2 must exist")
        self.assertEqual(self.framework_v2.code, "vn_address_v2")
        self.assertEqual(self.framework_v2.auth_type, "none")

        self.assertTrue(self.endpoint_v2, "Endpoint endpoint_vn_address_v2 must exist")
        self.assertEqual(self.endpoint_v2.framework_id, self.framework_v2)
        self.assertEqual(self.endpoint_v2.handler_type, "python")
        self.assertTrue(self.endpoint_v2.code, "Python handler code must be defined")

    def test_02_inbound_message_ingestion_and_processing_v2(self):
        """Verify queueing NQ60 v2 payload and creating 2-tier records with legacy mapping."""
        # Create a pre-existing legacy ward to test legacy mapping
        legacy_w = self.env["res.country.ward"].create({
            "name": "Legacy Source Ward",
            "code": "LEG_9901",
            "is_new": False,
        })

        payload = {
            "provinces": [
                {"code": 6661, "name": "NQ60 Test Province", "codename": "nq60_p1"},
            ],
            "wards": [
                {
                    "code": 666001,
                    "name": "NQ60 Consolidated Ward",
                    "codename": "nq60_w1",
                    "province_code": 6661,
                    "legacy_codes": ["LEG_9901"],
                },
            ],
        }

        msg = self.SyncService.enqueue_payload_v2(payload, process_now=True)
        self.assertTrue(msg.id)
        self.assertEqual(msg.state, "done", f"Message should be in 'done' state, error: {msg.error_details}")

        # Verify created state
        state = self.env["res.country.state"].search([("vn_code", "=", 6661)], limit=1)
        self.assertTrue(state, "Consolidated province must be created")
        self.assertEqual(state.name, "NQ60 Test Province")

        # Verify created consolidated ward
        ward = self.env["res.country.ward"].with_context(active_test=False).search([("code", "=", "666001")], limit=1)
        self.assertTrue(ward, "Consolidated ward must be created")
        self.assertEqual(ward.state_id, state)
        self.assertTrue(ward.is_new)
        self.assertIn(legacy_w, ward.map_with_ward_ids, "Legacy ward must be linked in map_with_ward_ids")

    def test_03_real_seed_records_verified_v2(self):
        """Verify real seed NQ60 records on odoo19 database."""
        # 1. Hanoi Ba Dinh consolidated ward
        w_ba_dinh = self.env.ref("dn_vn_address_nq60_connector.ward_real_nq60_ba_dinh", raise_if_not_found=False)
        self.assertTrue(w_ba_dinh, "Ward Ba Dinh must exist")
        self.assertEqual(w_ba_dinh.code, "4")
        self.assertTrue(w_ba_dinh.is_new)

        # Legacy ward link
        w_phuc_xa = self.env.ref("dn_vn_address_connector.ward_real_phuc_xa", raise_if_not_found=False)
        if w_phuc_xa:
            self.assertIn(w_phuc_xa, w_ba_dinh.map_with_ward_ids)

        # 2. Da Nang Hai Chau consolidated ward
        w_hai_chau = self.env.ref("dn_vn_address_nq60_connector.ward_real_nq60_hai_chau", raise_if_not_found=False)
        self.assertTrue(w_hai_chau, "Ward Hai Chau must exist")
        self.assertEqual(w_hai_chau.code, "20227")
        self.assertTrue(w_hai_chau.is_new)

        # 3. HCM Ben Nghe consolidated ward
        w_ben_nghe = self.env.ref("dn_vn_address_nq60_connector.ward_real_nq60_ben_nghe", raise_if_not_found=False)
        self.assertTrue(w_ben_nghe, "Ward Ben Nghe must exist")
        self.assertEqual(w_ben_nghe.code, "26734")
        self.assertTrue(w_ben_nghe.is_new)

        # 4. Message record
        msg_seed = self.env.ref("dn_vn_address_nq60_connector.msg_seed_v2", raise_if_not_found=False)
        self.assertTrue(msg_seed, "Seed message msg_seed_v2 must exist")
        self.assertEqual(msg_seed.state, "done")
