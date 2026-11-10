from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    vn_allow_mixed_usage = fields.Boolean(
        string="Allow Mixed Usage",
        default=False,
        tracking=True,
        help="Allow using this receivable/payable account flexibly across sales, purchases, "
             "and miscellaneous entries without strict document-type enforcement "
             "(e.g., Vietnamese Account 141 - Employee Advances, Account 131 - Customer Prepayments)."
    )
