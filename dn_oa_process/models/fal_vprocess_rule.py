# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
import logging

_logger = logging.getLogger(__name__)

class fal_vprocess_rule(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    _name = "fal.vprocess.rule"
    _description = "Rule"
    _order = "step_id,sequence,id"

    name = fields.Char("Name", default="Rule", tracking=True)
    active = fields.Boolean("Active", default=True, tracking=True)
    sequence = fields.Integer("Sequence", default=0, tracking=True)

    step_id = fields.Many2one('fal.vprocess.step', 'Step', tracking=True)
    v_process_id = fields.Many2one('fal.vprocess', 'Validation Process', related="step_id.process_id", store=True, readonly=True)
    user_ids = fields.Many2many('res.users', tracking=True)
    user_filter_id = fields.Many2one('ir.filters', 'User Filter', required=False, tracking=True)
    user_filter_domain = fields.Text(string='User Filter Domain', compute='_compute_user_filter_domain', tracking=True)

    user_domain_type = fields.Selection([('custom', 'Custom'), ('server', 'Server Action'), ('domain', 'Domain')], string='User Domain Type', default='custom', tracking=True)
    server_id = fields.Many2one('ir.actions.server', 'Server Action', required=False, tracking=True)
    custom_user_domain = fields.Text(string='Custom user domain', tracking=True)

    filter_id = fields.Many2one('ir.filters', 'Applies on', required=False, tracking=True)
    domain = fields.Text(string='Domain', compute='_compute_filter_domain')

    #Change related field into compute (Migration V13 - V15), ir_filter changed into single quote when saved in Odoo15
    #JSON.parse() string format must on double quote else error
    #Compute domain to reformat related field
    def _compute_user_filter_domain(self):
        for record in self:
            if record.user_filter_id and record.user_filter_id.domain:
                record.user_filter_domain = record.user_filter_id.domain.replace("'", '"')
                record.user_filter_domain = record.user_filter_domain.replace("(", "[")
                record.user_filter_domain = record.user_filter_domain.replace(")", "]")
            else:
                record.user_filter_domain = False

    def _compute_filter_domain(self):
        for record in self:
            if record.filter_id and record.filter_id.domain:
                record.domain = record.filter_id.domain.replace("'", '"')
                record.domain = record.domain.replace("(", "[")
                record.domain = record.domain.replace(")", "]")
            else:
                record.domain = False

    def _normalize_user_ids(self, value):
        if not value:
            return []
        if hasattr(value, 'ids'):
            return value.ids
        if isinstance(value, int):
            return [value]
        if isinstance(value, (list, tuple, set)):
            user_ids = []
            for item in value:
                if isinstance(item, int):
                    user_ids.append(item)
                elif isinstance(item, (list, tuple)) and item and isinstance(item[0], int):
                    user_ids.append(item[0])
                elif hasattr(item, 'ids'):
                    user_ids.extend(item.ids)
                elif hasattr(item, 'id'):
                    user_ids.append(item.id)
            return user_ids
        if isinstance(value, dict):
            for key in ('user_ids', 'ids', 'res_ids'):
                if key in value:
                    return self._normalize_user_ids(value[key])
        return []

    def get_allowed_user_ids(self):
        self.ensure_one()

        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        active_ids = self.env.context.get('active_ids') or ([active_id] if active_id else [])

        if self.user_domain_type == 'custom':
            return self.user_ids.ids

        if self.user_domain_type == 'domain':
            if not self.custom_user_domain or not str(self.custom_user_domain).strip():
                return self.env['res.users'].sudo().search([]).ids

            eval_context = {
                'uid': self.env.uid,
                'user': self.env.user,
                'context': dict(self.env.context),
                'active_model': active_model,
                'active_id': active_id,
                'active_ids': active_ids,
            }
            try:
                domain = safe_eval(self.custom_user_domain, eval_context)
            except Exception as e:
                _logger.error(str(e))
                return []

            if not isinstance(domain, (list, tuple)):
                return []

            if not domain:
                return self.env['res.users'].sudo().search([]).ids

            return self.env['res.users'].sudo().search(domain).ids

        if self.user_domain_type == 'server':
            if not self.server_id:
                return []

            try:
                result = self.sudo().server_id.with_context(
                    active_model=active_model,
                    active_id=active_id,
                    active_ids=active_ids,
                ).run()
            except Exception as e:
                _logger.error(str(e))
                return []

            return self.env['res.users'].sudo().browse(self._normalize_user_ids(result)).ids

        return []
