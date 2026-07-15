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
                    'voter', 'warehouse_manager', 'stock_controller', 'supervisor', 'receiver', 'chief_acc', 'hcns', 'unit_heads'):
                list_approver = record.current_approve_user_ids.ids
                field_map = {
                    'voter': 'voter_id',
                    'warehouse_manager': 'warehouse_manager_id',
                    'stock_controller': 'stock_controller_id',
                    'supervisor': 'supervisor_id',
                    'receiver': 'user_id',
                    'chief_acc': 'chief_acc_id',
                    'hcns': 'hcns_id',
                    'unit_heads': 'unit_heads_id',
                }
                field_name = field_map.get(record.trp_approve_config_line_id.manager_type)
                if field_name and hasattr(record, field_name):
                    user = getattr(record, field_name)
                    if user and user.id not in list_approver:
                        list_approver.append(user.id)
                record.current_approve_user_ids = [(6, 0, list_approver)]
