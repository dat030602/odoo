from odoo import models, fields, api
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_prevent_over_credit = fields.Boolean(string='Chặn hoạt động', default=False, help='Chặn hoạt động nếu vượt tín dụng', tracking=True)
    partner_group_id = fields.Many2one("res.partner.group", string="Nhóm đối tác", compute='_compute_partner_group')
    credit_group = fields.Monetary(string="Hạn mức tín dụng nhóm", related='partner_group_id.credit', store=True)

    def _compute_partner_group(self):
        for record in self:
            group = self.env['res.partner.group'].search([('partner_ids', 'in', record.id)], limit=1)
            record.partner_group_id = group.id if group else False
