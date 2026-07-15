# -*- coding: utf-8 -*-

from odoo import models


class CcvTongHopCongNoPhaiThu(models.Model):
    _inherit = 'ccv.tong.hop.cong.no.phai.thu'

    def action_print_xlsx_report(self):
        self.ensure_one()
        proxy = self.env['alpha.report'].sudo().create({
            'type': 'tong_hop_cong_no_phai_thu',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'account_id': self.account_id.id,
            'partner_id': self.partner_id.id,
            'partner_ids': [(6, 0, self.partner_ids.ids)],
            'report_type': self.report_type,
            'team_id': [(6, 0, self.team_id.ids)],
            'voter_id': self.voter_id.id,
            'chief_dept_id': self.chief_dept_id.id,
            'chief_acc_id': self.chief_acc_id.id,
            'unit_heads_id': self.unit_heads_id.id,
            'page_break': self.page_break,
        })
        for ln in self.line_ids:
            self.env['beta.report.line1'].sudo().create({
                'parent_id': proxy.id,
                'partner_id': ln.partner_id.id,
                'account_id': ln.account_id.id,
                'customer_name': ln.customer_name,
                'customer_code': ln.customer_code,
                'customer_group': ln.customer_group,
                'start_debit': ln.start_debit,
                'start_credit': ln.start_credit,
                'ps_debit': ln.ps_debit,
                'ps_credit': ln.ps_credit,
                'end_debit': ln.end_debit,
                'end_credit': ln.end_credit,
                'start_debit_nt': ln.start_debit_nt,
                'start_credit_nt': ln.start_credit_nt,
                'ps_debit_nt': ln.ps_debit_nt,
                'ps_credit_nt': ln.ps_credit_nt,
                'end_debit_nt': ln.end_debit_nt,
                'end_credit_nt': ln.end_credit_nt,
                'currency_id': ln.currency_id.id,
            })
        try:
            return self.env.ref('ccv_bao_cao.tong_hop_cong_no_phai_thu_xlsx_report').report_action(proxy)
        finally:
            pass
