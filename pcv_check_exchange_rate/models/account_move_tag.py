from odoo import fields, models, api, _


class AccountMoveTag(models.Model):
    _name = 'account.move.tag'
    _description = 'Account Move Tag'

    name = fields.Char(required=True, translate=True)
