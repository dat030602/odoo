# -*- coding: utf-8 -*-
from odoo.tests import tagged, TransactionCase


@tagged("post_install", "-at_install")
class TestVNAddressConnector(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Framework = cls.env["connector.framework"]
        cls.Endpoint = cls.env["connector.inbound.endpoint"]
        cls.Message = cls.env["connector.inbound.message"]
        cls.SyncService = cls.env["vn.address.connector.sync"]

        cls.framework_v1 = cls.env.ref("dn_vn_address_connector.preset_framework_vn_address_v1", raise_if_not_found=False)
        cls.endpoint_v1 = cls.env.ref("dn_vn_address_connector.endpoint_vn_address_v1", raise_if_not_found=False)

    def test_01_framework_preset_and_endpoint(self):
        """Verify Open API v1 connector framework preset and inbound endpoint exist."""
        self.assertTrue(self.framework_v1, "Framework preset vn_address_v1 must exist")
        self.assertEqual(self.framework_v1.code, "vn_address_v1")
        self.assertEqual(self.framework_v1.auth_type, "none")

        self.assertTrue(self.endpoint_v1, "Endpoint endpoint_vn_address_v1 must exist")
        self.assertEqual(self.endpoint_v1.framework_id, self.framework_v1)
        self.assertEqual(self.endpoint_v1.handler_type, "python")
        self.assertTrue(self.endpoint_v1.code, "Python handler code must be defined")

    def test_02_inbound_message_ingestion_and_processing(self):
        """Verify queueing payload into connector inbox and executing python handler."""
        payload = {
            "provinces": [
                {"code": 7771, "name": "Connector Test Province", "codename": "conn_p1"},
            ],
            "districts": [
                {"code": 77701, "name": "Connector Test District", "codename": "conn_d1", "province_code": 7771},
            ],
            "wards": [
                {"code": 777001, "name": "Connector Test Ward", "codename": "conn_w1", "district_code": 77701},
            ],
        }

        msg = self.SyncService.enqueue_payload_v1(payload, process_now=True)
        self.assertTrue(msg.id)
        self.assertEqual(msg.state, "done", f"Message should be in 'done' state, error: {msg.error_details}")

        # Verify created records
        state = self.env["res.country.state"].search([("vn_code", "=", 7771)], limit=1)
        self.assertTrue(state, "State must be created by connector handler")
        self.assertEqual(state.name, "Connector Test Province")

        district = self.env["res.country.district"].with_context(active_test=False).search([("code", "=", "77701")], limit=1)
        self.assertTrue(district, "District must be created by connector handler")
        self.assertEqual(district.state_id, state)

        ward = self.env["res.country.ward"].with_context(active_test=False).search([("code", "=", "777001")], limit=1)
        self.assertTrue(ward, "Ward must be created by connector handler")
        self.assertEqual(ward.district_id, district)
        self.assertEqual(ward.state_id, state)

    def test_03_real_seed_data_verified(self):
        """Verify that real seed records for Hanoi, Da Nang, and HCM exist on odoo19."""
        # 1. Hanoi Ba Dinh / Phuc Xa
        ba_dinh = self.env.ref("dn_vn_address_connector.district_real_ba_dinh", raise_if_not_found=False)
        self.assertTrue(ba_dinh, "District Ba Dinh must exist")
        self.assertEqual(ba_dinh.code, "1")

        phuc_xa = self.env.ref("dn_vn_address_connector.ward_real_phuc_xa", raise_if_not_found=False)
        self.assertTrue(phuc_xa, "Ward Phuc Xa must exist")
        self.assertEqual(phuc_xa.district_id, ba_dinh)

        # 2. Da Nang Hai Chau / Thach Thang
        hai_chau = self.env.ref("dn_vn_address_connector.district_real_hai_chau", raise_if_not_found=False)
        self.assertTrue(hai_chau, "District Hai Chau must exist")
        self.assertEqual(hai_chau.code, "490")

        thach_thang = self.env.ref("dn_vn_address_connector.ward_real_thach_thang", raise_if_not_found=False)
        self.assertTrue(thach_thang, "Ward Thach Thang must exist")
        self.assertEqual(thach_thang.district_id, hai_chau)

        # 3. HCM Quan 1 / Ben Nghe
        quan_1 = self.env.ref("dn_vn_address_connector.district_real_quan_1", raise_if_not_found=False)
        self.assertTrue(quan_1, "District Quan 1 must exist")
        self.assertEqual(quan_1.code, "760")

        ben_nghe = self.env.ref("dn_vn_address_connector.ward_real_ben_nghe", raise_if_not_found=False)
        self.assertTrue(ben_nghe, "Ward Ben Nghe must exist")
        self.assertEqual(ben_nghe.district_id, quan_1)

        # 4. Inbound message seed record
        seed_msg = self.env.ref("dn_vn_address_connector.msg_seed_v1", raise_if_not_found=False)
        self.assertTrue(seed_msg, "Seed message msg_seed_v1 must exist")
        self.assertEqual(seed_msg.state, "done")
