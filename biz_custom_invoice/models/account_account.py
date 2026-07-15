# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError

class AccountAccount(models.Model):
    _inherit = 'account.account'

    tax_account_collection_payment = fields.Boolean('Tax account for collection and payment',copy=False)