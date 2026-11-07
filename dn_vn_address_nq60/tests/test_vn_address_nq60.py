# -*- coding: utf-8 -*-
from unittest.mock import patch
from odoo.tests import tagged, TransactionCase


@tagged("post_install", "-at_install")
class TestVNAddressNQ60(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_vn = cls.env.ref("base.vn", raise_if_not_found=False)
        if not cls.country_vn:
            cls.country_vn = cls.env["res.country"].search([("code", "=", "VN")], limit=1)

        cls.state_anchor = cls.env["res.country.state"].search([
            ("country_id", "=", cls.country_vn.id),
            ("code", "=", "TEST_ANCHOR_NQ60"),
        ], limit=1)
        if not cls.state_anchor:
            cls.state_anchor = cls.env["res.country.state"].create({
                "name": "Test Anchor State",
                "code": "TEST_ANCHOR_NQ60",
                "vn_code": 8881,
                "country_id": cls.country_vn.id,
            })

    def test_01_nq60_address_format(self):
        """Test NQ60 2-tier address formatting (district omitted)."""
        Ward = self.env["res.country.ward"]
        Partner = self.env["res.partner"]

        ward = Ward.create({
            "name": "Consolidated Ward 1",
            "code": "CW1_NQ60",
            "state_id": self.state_anchor.id,
            "is_new": True,
        })

        partner = Partner.create({
            "name": "NQ60 Test Partner",
            "street": "456 Le Duan",
            "ward_id": ward.id,
            "state_id": self.state_anchor.id,
            "country_id": self.country_vn.id,
        })

        # Test full address computation (2-tier)
        self.assertIn("456 Le Duan", partner.full_address_vi)
        self.assertIn("Consolidated Ward 1", partner.full_address_vi)
        self.assertIn("Test Anchor State", partner.full_address_vi)

        # Test display address
        display = partner._display_address()
        self.assertIn("Consolidated Ward 1", display)
        self.assertIn("Test Anchor State", display)

        # Ensure district is not present
        _fmt, args = partner._prepare_display_address()
        self.assertEqual(args.get("ward_name"), "Consolidated Ward 1")
        self.assertEqual(args.get("district_name"), "")

    def test_02_state_merge_partners(self):
        """Test merging absorbed provinces into anchor province and updating partner records."""
        State = self.env["res.country.state"]
        Partner = self.env["res.partner"]

        state_absorbed = State.create({
            "name": "Absorbed Province Test",
            "code": "TEST_ABSORBED_NQ60",
            "vn_code": 8882,
            "country_id": self.country_vn.id,
        })

        partner = Partner.create({
            "name": "Partner in Absorbed Province",
            "street": "789 Tran Phu",
            "state_id": state_absorbed.id,
            "country_id": self.country_vn.id,
        })

        self.state_anchor.map_with_state_ids = [(4, state_absorbed.id)]
        self.state_anchor.action_merge_state_nq60()

        # Partner must now point to the anchor province
        self.assertEqual(partner.state_id, self.state_anchor)
        # Absorbed province must be archived
        self.assertFalse(state_absorbed.active)

    def test_03_ward_merge_partners(self):
        """Test merging legacy wards into consolidated ward and updating partner records."""
        Ward = self.env["res.country.ward"]
        Partner = self.env["res.partner"]

        ward_legacy = Ward.create({
            "name": "Legacy Ward Test",
            "code": "LW_TEST_NQ60",
            "state_id": self.state_anchor.id,
            "is_new": False,
        })

        ward_new = Ward.create({
            "name": "New Consolidated Ward Test",
            "code": "NW_TEST_NQ60",
            "state_id": self.state_anchor.id,
            "is_new": True,
        })

        partner = Partner.create({
            "name": "Partner in Legacy Ward",
            "street": "101 Nguyen Hue",
            "ward_id": ward_legacy.id,
            "state_id": self.state_anchor.id,
            "country_id": self.country_vn.id,
        })

        ward_new.map_with_ward_ids = [(4, ward_legacy.id)]
        ward_new.action_merge_ward_nq60()

        # Partner must now point to the consolidated ward
        self.assertEqual(partner.ward_id, ward_new)
        # Legacy ward must be archived
        self.assertFalse(ward_legacy.active)

    def test_04_sync_nq60_v2_mock(self):
        """Test API v2 sync creating 34 provinces and consolidated wards with is_new=True."""
        mock_p_v2 = [
            {"code": 8888, "name": "Mock NQ60 Province A", "codename": "mock_nq60_a", "division_type": "thanh_pho"},
            {"code": 8889, "name": "Mock NQ60 Province B", "codename": "mock_nq60_b", "division_type": "tinh"},
        ]
        mock_w_v2 = [
            {"code": 888801, "name": "Mock NQ60 Ward 1", "codename": "mock_w1", "province_code": 8888},
            {"code": 888901, "name": "Mock NQ60 Ward 2", "codename": "mock_w2", "province_code": 8889},
        ]

        def fake_fetch_v2(url, timeout=30):
            if url.endswith("/p/"):
                return mock_p_v2
            elif url.endswith("/w/"):
                return mock_w_v2
            return []

        with patch.object(type(self.env["res.country.state"]), "_fetch_api_json_v2", side_effect=fake_fetch_v2):
            self.env["res.country.state"]._sync_nq60_v2()

        s_a = self.env["res.country.state"].search([("vn_code", "=", 8888)], limit=1)
        self.assertTrue(s_a)
        self.assertEqual(s_a.name, "Mock NQ60 Province A")

        w_1 = self.env["res.country.ward"].search([("code", "=", "888801")], limit=1)
        self.assertTrue(w_1)
        self.assertEqual(w_1.state_id, s_a)
        self.assertTrue(w_1.is_new)

        # Idempotency check: re-run sync
        with patch.object(type(self.env["res.country.state"]), "_fetch_api_json_v2", side_effect=fake_fetch_v2):
            self.env["res.country.state"]._sync_nq60_v2()

        count_p = self.env["res.country.state"].search_count([("vn_code", "=", 8888)])
        count_w = self.env["res.country.ward"].search_count([("code", "=", "888801")])
        self.assertEqual(count_p, 1)
        self.assertEqual(count_w, 1)
