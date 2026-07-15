from odoo import fields, models, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    kd_report_html = fields.Html('Bảng Lương Kinh Doanh', compute='_compute_kd_report_html')
    is_kd_structure = fields.Boolean(compute='_compute_is_kd_structure')

    def _compute_is_kd_structure(self):
        for rec in self:
            rec.is_kd_structure = bool(rec.struct_id and ('Kinh Doanh' in rec.struct_id.name or 'KDVP' in rec.struct_id.name))

    def _compute_kd_report_html(self):
        for rec in self:
            if rec.struct_id and ('Kinh Doanh' in rec.struct_id.name or 'KDVP' in rec.struct_id.name):
                lines = rec.get_kd_custom_report_lines()
                html = '<table class="table table-sm o_list_table table-striped" style="width: 100%; border: 1px solid #e0e0e0;">'
                html += '<thead><tr style="background-color: #f8f9fa;"><th>Tên</th><th style="text-align: right;">Tổng</th></tr></thead><tbody>'
                for line in lines:
                    bold_style = 'font-weight: bold;' if line.get('is_bold') else ''
                    html += f'<tr style="{bold_style}">'
                    html += f'<td style="border-top: 1px solid #e0e0e0; padding: 0.3rem;">{line["name"]}</td>'
                    html += f'<td style="border-top: 1px solid #e0e0e0; padding: 0.3rem; text-align: right;">{line["total"]:,.0f}</td>'
                    html += '</tr>'
                html += '</tbody></table>'
                rec.kd_report_html = html
            else:
                rec.kd_report_html = '<p>Không khả dụng cho khối này</p>'

    def action_print_payslip_pdf(self):
        return self.env.ref('biz_payslip_pdf_report.action_report_payslip_pdf').report_action(self)

    def action_print_payslip_pdf_tree(self):
        return {
            'name': 'Payslip',
            "type": "ir.actions.act_url",
            'url': '/print/payslip-pdf?list_ids=%(list_ids)s' % {'list_ids': ','.join(str(x) for x in self.ids)},
            'target': 'self'
        }

    def get_kd_custom_report_lines(self):
        self.ensure_one()
        mappings = self.env['payslip.report.mapping'].search([('struct_id', '=', self.struct_id.id)], order='custom_sequence')
        rule_to_line = {l.salary_rule_id.id: l for l in self.line_ids}
        code_to_line = {l.code: l for l in self.line_ids if l.code}
        
        report_lines = []
        seq_to_val = {}
        for m in mappings:
            val = 0.0
            if m.rule_id:
                if m.rule_id.id in rule_to_line:
                    val = rule_to_line[m.rule_id.id].total
                elif m.rule_id.code and m.rule_id.code in code_to_line:
                    val = code_to_line[m.rule_id.code].total
            seq_to_val[m.custom_sequence] = val
            
        if 11 in seq_to_val:
            seq_to_val[11] = seq_to_val.get(6, 0) + seq_to_val.get(8, 0) + seq_to_val.get(10, 0)
        if 21 in seq_to_val:
            seq_to_val[21] = sum([seq_to_val.get(i, 0) for i in [11, 13, 14, 15, 16, 17, 18, 19, 20]])
        if 25 in seq_to_val:
            seq_to_val[25] = sum([seq_to_val.get(i, 0) for i in [22, 23, 24]])
            
        for m in mappings:
            report_lines.append({
                'index_display': str(m.custom_sequence),
                'name': m.custom_name,
                'unit': '',
                'total': seq_to_val.get(m.custom_sequence, 0.0),
                'is_bold': True if m.custom_sequence in [11, 21, 25, 38] else False
            })
        return report_lines

    def _get_rule_name(self, localdict, rule, employee_lang):
        return rule.with_context(lang=employee_lang).name

    def read(self, fields=None, load='_classic_read'):
        res = super(HrPayslip, self).read(fields=fields, load=load)
        if fields and 'line_ids' in fields:
            for val in res:
                if 'line_ids' in val and val['line_ids']:
                    lines = self.env['hr.payslip.line'].browse(val['line_ids'])
                    # Lọc bỏ các dòng có total = 0 (trừ các mã bắt buộc)
                    filtered_lines = lines.filtered(
                        lambda l: l.total != 0 or l.code in ['NC', 'BASIC', 'KPI', 'LNC', 'NET', 'TCONG', 'TTNC', 'TTN']
                    )
                    # Sắp xếp theo payslip_no (hoặc sequence)
                    sorted_lines = filtered_lines.sorted(key=lambda l: (l.salary_rule_id.payslip_no or 999, l.sequence or 999))
                    val['line_ids'] = sorted_lines.ids
        return res


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    number_rule_payslip = fields.Integer('Number', related='salary_rule_id.payslip_no')
    check_first = fields.Boolean('Invisible', compute='compute_check_first')

    def compute_check_first(self):
        for rec in self:
            rec.check_first = False
            if rec.total == 0 and rec.code not in ['NC', 'BASIC', 'KPI', 'LNC', 'NET', 'TCONG', 'TTNC', 'TTN']:
                rec.check_first = True
