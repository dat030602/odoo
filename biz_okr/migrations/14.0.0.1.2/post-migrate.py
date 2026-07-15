# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def _update_groups(env):
    env.ref('biz_okr.group_okr_manager').write({
        'implied_ids': [(6, 0, env.ref('biz_okr.group_okr_officer').ids)]
        })


def _update_ir_rules(env):
    env.ref('biz_okr.okr_node_all_rule').write({
        'groups': [(6, 0, env.ref('biz_okr.group_okr_officer').ids)]
        })


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_groups(env)
    _update_ir_rules(env)

