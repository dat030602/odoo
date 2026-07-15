# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.fields import Command

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    # INSERT_YOUR_CODE
    salary_gross = fields.Monetary(
        string="Lương xếp loại",
        compute="_compute_salary_gross",
        store=True,
        currency_field='currency_id'
    )
    advance_salary = fields.Monetary(
        string="Tiền tạm ứng",
        compute="_compute_advance_salary",
        store=True,
        currency_field='currency_id'
    )

    @api.depends('line_ids.total')
    def _compute_salary_gross(self):
        for payslip in self:
            gross_line = payslip.line_ids.filtered(lambda l: l.code == 'GROSS')
            payslip.salary_gross = gross_line.total if gross_line else 0.0

    @api.depends('line_ids.total')
    def _compute_advance_salary(self):
        for payslip in self:
            ttu_line = payslip.line_ids.filtered(lambda l: l.code == 'TTU')
            payslip.advance_salary = ttu_line.total if ttu_line else 0.0

    @api.depends('line_ids.total')
    def _compute_basic_net(self):
        super()._compute_basic_net()
        for payslip in self:
            # Chỉ ghi đè (hiển thị contract.wage) đối với các bảng lương Kinh doanh (struct_id 2, 5, 6)
            # Các bảng lương khác (Văn phòng, Sản xuất) vẫn giữ nguyên logic cũ để không bị ảnh hưởng.
            if payslip.contract_id and payslip.struct_id and payslip.struct_id.id in [2, 5, 6]:
                payslip.basic_wage = payslip.contract_id.wage
