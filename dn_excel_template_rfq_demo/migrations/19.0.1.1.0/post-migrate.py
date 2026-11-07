# -*- coding: utf-8 -*-
"""Post-migration script for dn_excel_template_rfq_demo version 19.0.1.1.0."""

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Seed RFQ Hetian Python Code Template upon upgrade."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.dn_excel_template_rfq_demo import _seed_rfq_demo_data
    _seed_rfq_demo_data(env)
