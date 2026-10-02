from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    dn_form_full_width = fields.Boolean(
        string='Full Width Form',
        default=False,
        help='Store the user preference for the full-width form toggle.',
    )
