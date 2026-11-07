# -*- coding: utf-8 -*-
from unittest.mock import patch
from psycopg2.errors import UniqueViolation
from odoo.tests import tagged, TransactionCase
from odoo.tools import mute_logger
from odoo.exceptions import ValidationError


@tagged("post_install", "-at_install")
class TestVNAddressV1(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_vn = cls.env.ref("base.vn", raise_if_not_found=False)
        if not cls.country_vn:
            cls.country_vn = cls.env["res.country"].search([("code", "=", "VN")], limit=1)

        # Use an isolated test state
        cls.state_test = cls.env["res.country.state"].search([
            ("country_id", "=", cls.country_vn.id),
            ("code", "=", "TEST_STATE_V1"),
        ], limit=1)
        if not cls.state_test:
            cls.state_test = cls.env["res.country.state"].create({
                "name": "Test State V1",
                "code": "TEST_STATE_V1",
                "vn_code": 9991,
                "country_id": cls.country_vn.id,
            })

    def test_01_models_and_constraints(self):
        """Test District and Ward creation, relations, and unique constraints."""
        District = self.env["res.country.district"]
        Ward = self.env["res.country.ward"]

        # Create district
        district = District.create({
            "name": "Test District 1",
            "code": "TD1",
            "state_id": self.state_test.id,
        })
        self.assertTrue(district.id)
        self.assertIn(district, self.state_test.district_ids)

        # Unique constraint test on District: duplicate (state_id, code)
        with mute_logger("odoo.sql_db"), self.assertRaises(Exception):
            with self.env.cr.savepoint():
                District.create({
                    "name": "Test District Duplicate",
                    "code": "TD1",
                    "state_id": self.state_test.id,
                })

        # Create ward
        ward = Ward.create({
            "name": "Test Ward 1",
            "code": "TW1",
            "district_id": district.id,
        })
        self.assertTrue(ward.id)
        self.assertEqual(ward.state_id, self.state_test)
        self.assertIn(ward, district.ward_ids)

        # Unique constraint test on Ward: duplicate (district_id, code)
        with mute_logger("odoo.sql_db"), self.assertRaises(Exception):
            with self.env.cr.savepoint():
                Ward.create({
                    "name": "Test Ward Duplicate",
                    "code": "TW1",
                    "district_id": district.id,
                })

    def test_02_partner_address_and_onchange(self):
        """Test partner address computation, formatting, and onchange reactivity."""
        District = self.env["res.country.district"]
        Ward = self.env["res.country.ward"]
        Partner = self.env["res.partner"]

        district = District.create({
            "name": "District Alpha",
            "code": "DA_V1",
            "state_id": self.state_test.id,
        })
        ward = Ward.create({
            "name": "Ward Beta",
            "code": "WB_V1",
            "district_id": district.id,
        })

        partner = Partner.create({
            "name": "VN Test Partner",
            "street": "123 Nguyen Trai",
            "ward_id": ward.id,
            "district_id": district.id,
            "state_id": self.state_test.id,
            "country_id": self.country_vn.id,
        })

        # Test full_address_vi computation
        self.assertIn("123 Nguyen Trai", partner.full_address_vi)
        self.assertIn("Ward Beta", partner.full_address_vi)
        self.assertIn("District Alpha", partner.full_address_vi)
        self.assertIn("Test State V1", partner.full_address_vi)

        # Test _prepare_display_address
        _fmt, args = partner._prepare_display_address()
        self.assertEqual(args.get("ward_name"), "Ward Beta")
        self.assertEqual(args.get("district_name"), "District Alpha")

        # Test display address
        displayed = partner._display_address()
        self.assertIn("Ward Beta", displayed)
        self.assertIn("District Alpha", displayed)

        # Test Onchange: select ward -> auto-populates district and state
        new_partner = Partner.new({
            "name": "Onchange Test Partner",
            "ward_id": ward.id,
        })
        new_partner._onchange_ward_id()
        self.assertEqual(new_partner.district_id, district)
        self.assertEqual(new_partner.state_id, self.state_test)
        self.assertEqual(new_partner.country_id, self.country_vn)

        # Test Onchange: change state -> clears mismatching district and ward
        other_state = self.env["res.country.state"].search([
            ("country_id", "=", self.country_vn.id),
            ("id", "!=", self.state_test.id),
        ], limit=1)
        if other_state:
            new_partner.state_id = other_state
            new_partner._onchange_state_id()
            self.assertFalse(new_partner.district_id)
            self.assertFalse(new_partner.ward_id)

    def test_03_company_address_sync(self):
        """Test bidirectional synchronization of district_id and ward_id between res.company and partner."""
        District = self.env["res.country.district"]
        Ward = self.env["res.country.ward"]
        Company = self.env["res.company"]

        district = District.create({
            "name": "Company District",
            "code": "CD_V1",
            "state_id": self.state_test.id,
        })
        ward = Ward.create({
            "name": "Company Ward",
            "code": "CW_V1",
            "district_id": district.id,
        })

        company = Company.create({
            "name": "VN Test Subsidiary",
            "state_id": self.state_test.id,
            "district_id": district.id,
            "ward_id": ward.id,
        })

        self.assertEqual(company.partner_id.district_id, district)
        self.assertEqual(company.partner_id.ward_id, ward)

        # Update partner directly, company should recompute
        district_2 = District.create({
            "name": "Company District 2",
            "code": "CD2_V1",
            "state_id": self.state_test.id,
        })
        company.partner_id.district_id = district_2
        self.assertEqual(company.district_id, district_2)

    def test_04_sync_provinces_v1_mock(self):
        """Test API v1 address synchronization and idempotency using mock payloads."""
        mock_p = [
            {"code": 9998, "name": "Mock Province 1", "codename": "mock_p1", "division_type": "tinh"},
            {"code": 9999, "name": "Mock Province 2", "codename": "mock_p2", "division_type": "thanh_pho"},
        ]
        mock_d = [
            {"code": 99801, "name": "Mock District 1", "codename": "mock_d1", "province_code": 9998},
            {"code": 99802, "name": "Mock District 2", "codename": "mock_d2", "province_code": 9999},
        ]
        mock_w = [
            {"code": 998001, "name": "Mock Ward 1", "codename": "mock_w1", "district_code": 99801},
            {"code": 998002, "name": "Mock Ward 2", "codename": "mock_w2", "district_code": 99802},
        ]

        def fake_fetch(url, timeout=30):
            if url.endswith("/p/"):
                return mock_p
            elif url.endswith("/d/"):
                return mock_d
            elif url.endswith("/w/"):
                return mock_w
            return []

        with patch.object(type(self.env["res.country.state"]), "_fetch_api_json", side_effect=fake_fetch):
            self.env["res.country.state"]._sync_addresses_v1()

        s1 = self.env["res.country.state"].search([("vn_code", "=", 9998)], limit=1)
        self.assertTrue(s1)
        self.assertEqual(s1.name, "Mock Province 1")

        d1 = self.env["res.country.district"].search([("code", "=", "99801")], limit=1)
        self.assertTrue(d1)
        self.assertEqual(d1.state_id, s1)

        w1 = self.env["res.country.ward"].search([("code", "=", "998001")], limit=1)
        self.assertTrue(w1)
        self.assertEqual(w1.district_id, d1)
        self.assertEqual(w1.state_id, s1)

        # Test idempotency: re-run sync
        with patch.object(type(self.env["res.country.state"]), "_fetch_api_json", side_effect=fake_fetch):
            self.env["res.country.state"]._sync_addresses_v1()

        # Count records to ensure no duplicates created
        s_count = self.env["res.country.state"].search_count([("vn_code", "=", 9998)])
        d_count = self.env["res.country.district"].search_count([("code", "=", "99801")])
        w_count = self.env["res.country.ward"].search_count([("code", "=", "998001")])
        self.assertEqual(s_count, 1)
        self.assertEqual(d_count, 1)
        self.assertEqual(w_count, 1)
