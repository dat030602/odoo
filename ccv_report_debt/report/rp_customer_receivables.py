import json
from odoo import api, fields, models, _
from datetime import datetime, timedelta
from .component import format_date, vietnam_number, format_float_number, format_date_vi
import logging
_logger = logging.getLogger(__name__)

class ReportAccountingBalanceSheet(models.AbstractModel):
    _name = 'report.ccv_report_debt.rp_customer_receivables'
    _description = 'rp_customer_receivables'

    def get_qr_url(self, amount):
        config = self.env['vietqr.bank.config'].search([('is_default', '=', True)], limit=1)
        config = config.print_qr_id
        account_number = config.partner_bank_id.acc_number
        template_code = config.template_code
        bank_bin = config.vietqr_bank_id.bin
        bank_info = "Thanh toán công nợ"
        qr_url = f"https://api.vietqr.io/image/{bank_bin}-{account_number}-{template_code}.jpg?amount={amount}&addInfo={bank_info}"
        return qr_url

    def hanlde_tong_hop(self, docs, line_ids, line_credit, line_debit):
        return [
            {
                'company_id': self.env.company,
                'partner_id': partner_id,
                'parent_id': docs,
                'start_credit': sum(line_ids.filtered(lambda x: x.partner_id == partner_id).mapped('start_credit')),
                'start_debit': sum(line_ids.filtered(lambda x: x.partner_id == partner_id).mapped('start_debit')),
                'credit': sum(line_ids.filtered(lambda x: x.partner_id == partner_id).mapped(line_credit)),
                'debit': sum(line_ids.filtered(lambda x: x.partner_id == partner_id).mapped(line_debit)),
            } for partner_id in line_ids.mapped('partner_id')
        ]

    def _get_detail_start_balance(self, partner_lines, line_credit, line_debit):
        fields_map = partner_lines._fields
        start_lines = partner_lines.filtered(lambda line: (
            ('date' not in fields_map or not line.date)
            and ('move_id' not in fields_map or not line.move_id)
            and (line_debit not in fields_map or not line[line_debit])
            and (line_credit not in fields_map or not line[line_credit])
            and (line.start_debit or line.start_credit or line.end_debit or line.end_credit)
        ))
        if not start_lines:
            return 0, 0
        start_line = start_lines[0]
        start_debit = start_line.start_debit or start_line.end_debit
        start_credit = start_line.start_credit or start_line.end_credit
        return start_debit, start_credit
    
    def hanlde_chi_tiet(self, docs, line_ids, line_credit, line_debit):
        data = []
        for partner_id in line_ids.mapped('partner_id'):
            partner_lines = line_ids.filtered(lambda x: x.partner_id == partner_id)
            start_debit, start_credit = self._get_detail_start_balance(partner_lines, line_credit, line_debit)
            data.append({
                'company_id': self.env.company,
                'partner_id': partner_id,
                'parent_id': docs,
                'start_credit': start_credit,
                'start_debit': start_debit,
                'credit': sum(partner_lines.mapped(line_credit)),
                'debit': sum(partner_lines.mapped(line_debit)),
            })
        return data

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['alpha.report'].browse(docids)
        #beta_line1_ids: Tong hop cong no phai thu
        #beta_line2_ids: Tong hop cong no phai tra
        #beta_line3_ids: Tong hop cong no phai thu USD
        #beta_line4_ids: Tong hop cong no phai tra USD
        #beta_line5_ids: Chi tiết công nợ phai tra USD
        #beta_line6_ids: Chi tiết cong no phai thu USD
        #line2_ids: Chi tiết công nợ phải trả
        #line3_ids: Chi tiết công nợ phải thu
        if docs.type == 'tong_hop_cong_no_phai_thu':
            line_ids = docs.beta_line1_ids
        elif docs.type == 'tong_hop_cong_no_phai_tra':
            line_ids = docs.beta_line2_ids
        elif docs.type == 'tong_hop_cong_no_phai_thu_usd':
            line_ids = docs.beta_line3_ids
        elif docs.type == 'tong_hop_cong_no_phai_tra_usd':
            line_ids = docs.beta_line4_ids
        elif docs.type == 'chi_tiet_cong_no_phai_tra_usd':
            line_ids = docs.beta_line5_ids
        elif docs.type == 'chi_tiet_cong_no_phai_thu_usd':
            line_ids = docs.beta_line6_ids
        elif docs.type == 'chi_tiet_cong_no_phai_thu':
            line_ids = docs.line3_ids
        elif docs.type == 'chi_tiet_cong_no_phai_tra':
            line_ids = docs.line2_ids

        line_credit = 'credit' if 'credit' in line_ids._fields else 'ps_credit'
        line_debit = 'debit' if 'debit' in line_ids._fields else 'ps_debit'
        if docs.type in ('tong_hop_cong_no_phai_thu','tong_hop_cong_no_phai_tra','tong_hop_cong_no_phai_thu_usd','tong_hop_cong_no_phai_tra_usd'):
            obj = self.hanlde_tong_hop(docs, line_ids, line_credit, line_debit)
        else:
            obj = self.hanlde_chi_tiet(docs, line_ids, line_credit, line_debit)
        
        
        return {
            'doc_ids': docids,
            'doc_model': 'alpha.report',
            'docs': docs,
            'line_ids': obj,
            'format_float_number': format_float_number,
            'format_date': format_date,
            'format_date_vi': format_date_vi,
            'vietnam_number': vietnam_number,
            'get_qr_url': self.get_qr_url,
        }
