from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    transaction_code = fields.Char(string='Transaction Code', readonly=True, tracking=True)
    acc_counterpart_no = fields.Char(string='Counterpart Account Number', readonly=True, tracking=True)
    acc_counterpart_name = fields.Char(string='Counterpart Account Name', readonly=True, tracking=True)
    ref_src = fields.Char(string='Reference Source', readonly=True, tracking=True)

    @api.onchange('acc_counterpart_no')
    def _onchange_acc_counterpart_no(self):
        if self.acc_counterpart_no:
            self.partner_bank_id = self.env['res.partner.bank'].search([('acc_number', '=', self.acc_counterpart_no)], limit=1)
