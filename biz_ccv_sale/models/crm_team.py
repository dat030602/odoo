from odoo import api, fields, models, _
import json


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    member_ids_domain = fields.Many2many(
        'res.users', compute='_compute_member_ids_domain')
    member_ids = fields.Many2many(
        'res.users', domain='[("id", "not in", member_ids_domain)]')

    @api.depends('member_company_ids')
    def _compute_member_ids_domain(self):
        for team in self:
            member_ids = self.env['crm.team'].search([]).mapped('member_ids')
            domain = [
                ('share', '=', False),
                ('company_ids', 'in', team.member_company_ids.ids),
                ('id', 'in', member_ids.ids)
            ]
            team.member_ids_domain = self.env['res.users'].search(domain).ids
    
    @api.onchange('member_ids')
    def _onchange_member_ids(self):
        self._compute_member_ids_domain()
