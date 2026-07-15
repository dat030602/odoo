# -*- coding: utf-8 -*-
from odoo import models, api


class TrpApprove(models.Model):
    _inherit = 'trp.approve'

    @api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.manager_type',
                 'trp_approve_config_line_id.user_ids',
                 'trp_approve_config_line_id.job_ids')
    def _compute_current_approve_users(self):
        super()._compute_current_approve_users()
        for record in self:
            if record.trp_approve_config_line_id and record.trp_approve_config_line_id.manager_type in (
                    'creator', 'commercial_department'):
                list_approver = record.current_approve_user_ids.ids
                field_map = {
                    'creator': ('creator_id',),
                    'commercial_department': ('commercial_department_id', 'chief_trade_id'),
                }
                field_names = field_map.get(record.trp_approve_config_line_id.manager_type, ())
                for field_name in field_names:
                    if hasattr(record, field_name):
                        user = getattr(record, field_name)
                        if user and user.id not in list_approver:
                            list_approver.append(user.id)
                        break
                record.current_approve_user_ids = [(6, 0, list(set(list_approver)))]
