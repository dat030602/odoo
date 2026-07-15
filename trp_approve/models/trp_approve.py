# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval
from datetime import datetime, date
import ast
import logging

_logger = logging.getLogger(__name__)


class TrpApprove(models.Model):
    _name = 'trp.approve'

    is_user_current = fields.Boolean(compute='_compute_is_user_current', string="Người duyệt hiện tại", default=False,
                                     copy=False)
    trp_approve_config_line_id = fields.Many2one('trp.approve.config.line', string="Lịch sử duyệt", copy=False)
    delegate_approver_ids = fields.Many2many('res.users', string="Người duyệt ủy quyền")
    current_approve_user_ids = fields.Many2many('res.users', 'trp_approve_id', 'res_user_id', \
                                                'purchase_requisition_current_approve_user_ids',
                                                string="Người duyệt hiện tại", compute='_compute_current_approve_users')
    approve_next_action = fields.Char('Hành động kế tiếp')
    approve_state_init = fields.Char('Trạng thái hiện tại')
    approve_state_next = fields.Char('Trạng thái tiếp theo', default="approve")

    trp_approve_reason_id = fields.Many2one("trp.approve.reason", string="Lý do")
    trp_approve_reason_note = fields.Text(string="Mô tả")

    def write(self, vals):
        self = self.sudo()
        if 'delegate_approver_ids' in vals:
            his_data = {}
            for record in self:
                his_data[record.id] = record.delegate_approver_ids
        res = super().write(vals)
        if 'delegate_approver_ids' in vals:
            for record in self:
                add_data = record.delegate_approver_ids - his_data[record.id]
                del_data = his_data[record.id] - record.delegate_approver_ids
                res_history = self.env["trp.approve.history"].search(
                    [('res_model', '=', self._name), ('res_id', '=', record.id),
                     ('trp_approve_config_line_id', '=', record.trp_approve_config_line_id.id)], order='id desc',
                    limit=1)
                if res_history:
                    self.create_action_activity(add_data.ids, res_history.id)
                    if del_data:
                        self.env['mail.activity'].search([('user_id', 'in', del_data.ids), ('res_id', '=', record.id), \
                                                          ('res_model', '=', self._name)]).unlink()
        return res

    def create_action_activity(self, user_ids, his_id):
        todo_act = self.env['mail.activity.type'].search([('name', '=', 'To Do')], limit=1)
        res_model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
        activity_data = []
        for user_id in user_ids:
            activity = self.env['mail.activity'].search([('user_id', '=', user_id), ('res_id', '=', self.id), ('res_model', '=', self._name), ('trp_approve_history_id', '=', his_id)])
            if his_id and not activity:
                activity_data.append({
                    'activity_type_id': todo_act.id or False,
                    'date_deadline': fields.Date.today(),
                    'user_id': user_id,
                    'res_id': self.id,
                    'res_model': self._name,
                    'res_model_id': res_model_id.id,
                    'trp_approve_history_id': his_id,
                })
        if activity_data:
            self.env['mail.activity'].create(activity_data)

    def _compute_is_user_current(self):
        for record in self:
            return_value = False
            if record.trp_approve_config_line_id:
                return_value = record.check_user()
            elif record.state == 'approve':
                return_value = True

            record.is_user_current = return_value

    @api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.manager_type',
                 'trp_approve_config_line_id.user_ids', \
                 'trp_approve_config_line_id.job_ids')
    def _compute_current_approve_users(self):
        for record in self:
            list_approver = []
            if record.trp_approve_config_line_id:
                if record.trp_approve_config_line_id.user_ids:
                    list_approver = record.trp_approve_config_line_id.user_ids.ids

                for line in record.trp_approve_config_line_id.job_ids:
                    list_approver += line.employee_ids.ids

                if record.trp_approve_config_line_id.manager_type:
                    if record.trp_approve_config_line_id.manager_type == "manager":
                        user_manager = record.create_uid.department_id.manager_id.user_id.id
                        if user_manager:
                            list_approver.append(user_manager)
                    elif record.trp_approve_config_line_id.manager_type == "parent":
                        user_parent = record.create_uid.employee_id.parent_id.user_id.id
                        if user_parent:
                            list_approver.append(user_parent)
                    elif record.trp_approve_config_line_id.manager_type == "delegate":
                        approved_user_ids = record.trp_approve_history_ids.mapped('approve_user_id')
                        list_approver += (record.delegate_approver_ids - approved_user_ids).ids
                    elif record.trp_approve_config_line_id.manager_type == "loading":
                        # For Bốc xếp - use loading_id field if available
                        if hasattr(record, 'loading_id') and record.loading_id:
                            list_approver.append(record.loading_id.id)
                if len(record.delegate_approver_ids) > 0:
                    list_approver += record.delegate_approver_ids.ids

                record.current_approve_user_ids = [(6, 0, list_approver)]
            else:
                record.current_approve_user_ids = False

    def check_user(self):
        is_exists = False
        list_approver = []

        if not self.current_approve_user_ids.exists():
            return True

        # Người duyệt bước này
        if self.current_approve_user_ids:
            list_approver += self.current_approve_user_ids.ids

        if self.env.user.id in list_approver:
            is_exists = True
        
        return is_exists

    def create_approve(self):
        res_approve_line, res_new = self._create_approve()
        dict_trans = {}
        if res_new and res_approve_line:
            dict_trans = {
                'trp_approve_config_line_id': res_approve_line.id,
                'state': self.approve_state_next,
                'delegate_approver_ids': [(6, 0, res_approve_line.delegate_approver_ids.ids)],
            }
            self.sudo().write(dict_trans)
            if not res_approve_line.is_applied:
                res_approve_line.write({
                    'is_applied': True
                })
            if self.check_user():
                self.action_agree()
                if not self.trp_approve_config_line_id:
                    dict_trans = True
            else:
                self.create_action_activity(self.current_approve_user_ids.ids, res_new.id)

        return dict_trans

    def _create_approve(self):
        context = self.env.context
        domain_by_type = context.get('approve_type', 'new')
        to_check_sale_request = context.get('to_check_sale_request', False)

        # Kiểm tra cấu hình duyệt thỏa điều kiện
        res_approve = self.env['trp.approve.config'].search(
            [('res_model', '=', self._name), ('date_effective', '<=', str(self.create_date.date())), '|',
             ('date_expiration', '=', None),
             ('date_expiration', '>=', self.create_date.date())], order="date_effective desc, id desc", limit=1)
        config_lines = res_approve.trp_approve_config_line_ids
        cur_config_line = self.trp_approve_config_line_id
        if config_lines:
            to_get = False
            res_approve_line = self.env['trp.approve.config.line']
            if not cur_config_line:
                res_approve_line = config_lines[0]
            else:
                for config_line in config_lines:
                    if to_get:
                        if not to_check_sale_request or (to_check_sale_request and config_line.approver_field != 'sale_manager_id'):
                            res_approve_line |= config_line
                            break
                        else:
                            continue
                    if config_line == cur_config_line:
                        to_get = True
            if res_approve_line:
                dict_history = {
                    'trp_approve_config_line_id': res_approve_line.id,
                    self._fields['trp_approve_history_ids'].inverse_name: self.id,
                    'res_model': self._name,
                    'res_id': self.id,
                    'user_id': self.env.user.id,
                    'date': datetime.now(),
                    'type': domain_by_type,
                }
                # Add specific model fields
                if self._name == 'payment.request':
                    dict_history['payment_request_id'] = self.id
                elif self._name == 'sale.sign.requests':
                    dict_history['sale_sign_requests_id'] = self.id
                elif self._name == 'purchase.sign.requests':
                    dict_history['purchase_sign_requests_id'] = self.id
                elif self._name == 'details.sales.book.by.customer':
                    dict_history['dsk_customer_id'] = self.id
                elif self._name == 'rp.san.luong.nhap.xuat':
                    dict_history['rp_san_luong_nhap_xuat_id'] = self.id
                res_new = self.env['trp.approve.history'].create(dict_history)
                return res_approve_line, res_new
        return False, False

    def action_agree(self):
        # dict_agree = {}
        self = self.sudo()
        if not self.is_user_current:
            return
        if self.trp_approve_config_line_id:
            res_history = self.env["trp.approve.history"].search(
                [('res_model', '=', self._name), ('res_id', '=', self.id),
                 ('trp_approve_config_line_id', '=', self.trp_approve_config_line_id.id)], order='id desc', limit=1)

            dict_history = {
                'approve_user_id': self.env.user.id if self.current_approve_user_ids.exists() else False,
                'approve_date': datetime.now(),
                'delegate_approver_ids': [(6, 0, self.delegate_approver_ids.ids)],

            }

            # If approval_mode is 'all', add current user to all_approved_user_ids and only close their activity
            if self.trp_approve_config_line_id.approval_mode == 'all':
                # Track current user as approved (add to many2many, do not overwrite approve_user_id permanently)
                existing_approved = res_history[0].all_approved_user_ids
                new_approved_ids = list(set(existing_approved.ids + [self.env.user.id]))
                dict_history['all_approved_user_ids'] = [(6, 0, new_approved_ids)]
                res_history[0].write(dict_history)
                # Only close current user's activity, not all activities
                self.env['mail.activity'].search([
                    ('trp_approve_history_id', '=', res_history.id),
                    ('user_id', '=', self.env.user.id)
                ]).with_context(skip_approve_done=True).action_done()
            else:
                res_history[0].write(dict_history)
                self.env['mail.activity'].search([('trp_approve_history_id', '=', res_history.id)]).with_context(skip_approve_done=True).action_done()
            if dict_history:
                # Check if all required users have approved when approval_mode is 'all'
                if self.trp_approve_config_line_id.approval_mode == 'all':
                    # Get all required approvers for this level
                    required_approvers = self.current_approve_user_ids
                    # Get all users who have approved this level (from all_approved_user_ids)
                    approved_users = res_history[0].all_approved_user_ids

                    # Check if all required approvers have approved
                    missing_approvers = required_approvers - approved_users
                    if missing_approvers:
                        # Not all users have approved yet, don't move to next step
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'Thông báo',
                                'message': f'Bạn đã duyệt thành công. Còn {len(missing_approvers)} người cần duyệt thêm.',
                                'type': 'success',
                                'sticky': False,
                            }
                        }

                # If approval_mode is 'any' or all users have approved, proceed
                if self.trp_approve_config_line_id.do_agree:
                    dict_agree = ast.literal_eval(self.trp_approve_config_line_id.do_agree)
                    self.write(dict_agree)

                return self.with_context(approve_type=self.state == 'approve' and 'new' or 'cancel').check_next_approve()
        else:
            return self.with_context(approve_type=self.state == 'approve' and 'new' or 'cancel').check_next_approve()

    # return dict_agree

    def check_next_approve(self):
        res_approve_line, res_new = self._create_approve()
        if res_new and res_approve_line:
            dict_trans = {
                'trp_approve_config_line_id': res_approve_line.id,
                'state': self.approve_state_next,
                'delegate_approver_ids': [(6, 0, res_approve_line.delegate_approver_ids.ids)]
            }
            self.write(dict_trans)

            if self.check_user():
                self.action_agree()
            else:
                self.create_action_activity(self.current_approve_user_ids.ids, res_new and res_new.id or False)
        if not bool(res_new):
            self.approve_state_next = 'approved'
            self.approve_next_action = False
            dict_trans = {
                'trp_approve_config_line_id': False,
                'state': self.approve_state_next,
            }
            self.write(dict_trans)
            if self.approve_next_action:
                return getattr(self, self.approve_next_action)()
        return True

    def action_refuse(self):
        self = self.sudo()
        if not self.is_user_current:
            return
        if self.state == 'cancel':
            return
        self.state = 'refuse'
        return {
            'target': 'new',
            'view_mode': 'form',
            'res_model': 'trp.approve.config.reason',
            'type': 'ir.actions.act_window',
            'context': {
                'default_res_id': self.id,
                'default_res_model': self._name,
                'default_trp_approve_config_line_id': self.trp_approve_config_line_id.id,
            }
        }

    def get_signer_filter(self):
        self.ensure_one()
        signs = []
        signs.append({
            'title': 'Người đề nghị',
            'user_id': self.user_id,
            'is_signed': True,
            'priority': 0,
            'allow_sign': 0,
            'level': -1,
        })
        trp_approve_config_id = self.trp_approve_history_ids.mapped('trp_approve_config_line_id').mapped('trp_approve_config_id')
        if trp_approve_config_id:
            for trp_approve_config_line_id in trp_approve_config_id[0].trp_approve_config_line_ids:
                title = trp_approve_config_line_id.title
                history = self.trp_approve_history_ids.filtered(lambda l: l.trp_approve_config_line_id == trp_approve_config_line_id)
                user_ids = history.approve_user_id if history and history.approve_user_id else (trp_approve_config_line_id.user_ids or self.current_approve_user_ids)
                
                # Kiểm tra xem user_ids có rỗng không
                if user_ids:
                    user_id = user_ids[0]
                    is_signed = True if history and history.approve_user_id else False
                else:
                    user_id = False
                    is_signed = False
                
                signs.append({
                    'title': title,
                    'user_id': user_id,
                    'is_signed': is_signed,
                    'priority': trp_approve_config_line_id.priority,
                    'allow_sign': trp_approve_config_line_id.allow_sign,
                    'level': trp_approve_config_line_id.level,
                })
                
        signs = sorted(signs, key=lambda x: x.get('level', 0))
        return signs
