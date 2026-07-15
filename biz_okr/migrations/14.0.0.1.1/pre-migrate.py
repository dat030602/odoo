# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def _adjust_okr_success_points_threshold(env):
    env.cr.execute("""
    ALTER TABLE okr_node ADD COLUMN IF NOT EXISTS okr_success_points_threshold double precision;
    UPDATE okr_node SET okr_success_points_threshold = 0.7 WHERE okr_success_points_threshold < 0 OR okr_success_points_threshold > 1
    """)
    env.cr.execute("""
    ALTER TABLE res_company ADD COLUMN IF NOT EXISTS okr_success_points_threshold double precision;
    UPDATE res_company SET okr_success_points_threshold = 0.7 WHERE okr_success_points_threshold < 0 OR okr_success_points_threshold > 1
    """)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _adjust_okr_success_points_threshold(env)

