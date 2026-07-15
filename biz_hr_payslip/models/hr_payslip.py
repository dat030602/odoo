# -*- coding: utf-8 -*-
import time
import babel
from odoo import models, fields, api, tools, _
from datetime import datetime


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')
    def _compute_input_line_ids(self):
        res = super(HrPayslip, self)._compute_input_line_ids()
        for slip in self:      
            date_from = slip.date_from
            date_to = slip.date_to
            slip.input_line_ids = [(5,)]
            input_line_ids = slip.get_inputs([slip.contract_id], date_from, date_to)
            for val in input_line_ids:
                exits = slip.input_line_ids.filtered(lambda x: x.input_type_id.id == val['input_type_id'])
                # if exits:
                #     exits.update(val)
                # else:
                slip.update({
                    'input_line_ids': [(0, 0, val)]
                })

        return res


    def get_inputs(self, contract_ids, date_from, date_to):
        return []

    def _get_localdict(self):
        dict_return = super(HrPayslip,self)._get_localdict()
        if dict_return.get('same_type_input_lines'):
            dict_return.update({'same_type_input_lines': {}})
        return dict_return

