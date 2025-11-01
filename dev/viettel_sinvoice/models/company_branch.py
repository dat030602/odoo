# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_HEADER = {
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8'
}


class CompanyBranch(models.Model):
    _name = 'company.branch'
    _description = 'Company Branch'

    partner_id = fields.Many2one('res.partner', 'Partner')
    name = fields.Char('Branch', related='partner_id.name',store=True)
    vat = fields.Char('VAT')
    template_ids = fields.One2many('viettel.sinvoice.template', 'branch_id', string='Templates')
    templates_count = fields.Integer('Templates', compute='_compute_templates_count')
    bank = fields.Char('Bank')
    acc_number = fields.Char('Account Number')
    logo = fields.Image('Account Logo')

    @api.constrains('bank', 'acc_number')
    def _check_validate_acc_number_bank(self):
        for record in self:
            if record.bank and record.acc_number:
                banks = record.bank.split(';')
                acc_numbers = self.acc_number.split(';')
                if len(banks) != len(acc_numbers):
                    raise UserError('Số tài khoản ngân hàng phải bằng số tên ngân hàng tương ứng được cách bỏi dấu ";" !')

    def get_description_banks(self):
        if not self.bank or not self.acc_number:
            return ()
        else:
            banks = self.bank.split(';')
            acc_number = self.acc_number.split(';')
        rlt = [bk[0] + ' tại ' + bk[1] for bk in tuple(zip(banks, acc_number))]
        return rlt

    def _compute_templates_count(self):
        for br in self:
            br.templates_count = len(br.template_ids)

    def name_get(self):
        return [(branch.id, "%s / %s" % (branch.name, branch.vat)) for branch in self]

    def action_view_templates(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('viettel_sinvoice.action_open_viettel_viettel_sinvoice_template')
        action['domain'] = [('branch_id', 'in', self.mapped('id'))]
        action['context'] = dict(self._context, create=False)
        return action
