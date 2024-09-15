# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models, api, tools
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    cashier = fields.Many2one(comodel_name='res.users', string="Nhân viên", help="Nhân viên chịu trách nhiệm xác nhận thanh toán.", readonly=True)