from odoo import models, fields, api
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartnerGroup(models.Model):
    _name = "res.partner.group"

    name = fields.Char(string="Tên nhóm đối tác", required=True)
    description = fields.Text(string="Mô tả")
    partner_ids = fields.Many2many("res.partner", string="Đối tác")
    active = fields.Boolean(string="Kích hoạt", default=True)
    credit_limit = fields.Monetary(string="Hạn mức tín dụng", default=0.0)
    credit = fields.Monetary(string="Dư có", compute='_compute_credit')
    debit_limit = fields.Monetary(string="Hạn mức nợ", default=0.0)
    debit = fields.Monetary(string="Dư nợ", compute='_compute_debit')
    currency_id = fields.Many2one("res.currency", string="Loại tiền tệ", required=True, default=lambda self: self.env.company.currency_id)

    @api.constrains('partner_ids')
    def _check_unique_partners(self):
        groups = self.env['res.partner.group'].search([]) - self
        for group in groups:
            partner_set = set()
            for partner in group.partner_ids:
                if partner.id in partner_set:
                    raise UserError(f"Đối tác {partner.name} đã tồn tại trong nhóm đối tác {group.name}.")
                partner_set.add(partner.id)

    @api.depends('partner_ids.credit')
    def _compute_credit(self):
        for record in self:
            total_credit = sum(partner.credit for partner in record.partner_ids)
            record.credit = total_credit
    
    @api.depends('partner_ids.debit')
    def _compute_debit(self):
        for record in self:
            total_debit = sum(partner.debit for partner in record.partner_ids)
            record.debit = total_debit
