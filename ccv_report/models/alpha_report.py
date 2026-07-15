# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date, time


class AlphaReport(models.TransientModel):
    _inherit = 'alpha.report'

    def action_print_pdf_report(self):
        if self.type == 'tong_hop_cong_no_nhan_vien':
            return self.env.ref('ccv_sql.tong_hop_cong_no_nhan_vien_report').report_action(self)
        elif self.type == 'so_chi_tiet_ke_toan_quy_tien_mat':
            return self.env.ref('ccv_sql.so_chi_tiet_ke_toan_quy_tien_mat_report').report_action(self)
        elif self.type == "chi_tiet_cong_no_phai_tra":
            if self.partner_type == 'out':
                return self.env.ref('ccv_report.chi_tiet_cong_no_phai_tra_report_ccv_report').report_action(self)
            else:
                return self.env.ref('ccv_report.chi_tiet_cong_no_phai_tra_trong_nuoc_report_ccv_report').report_action(self)
        elif self.type == "chi_tiet_cong_no_phai_thu":
            return self.env.ref('ccv_sql.chi_tiet_cong_no_phai_thu_report').report_action(self)
        elif self.type == "giay_thanh_toan_tien_tam_ung":
            return self.env.ref('ccv_sql.giay_thanh_toan_tien_tam_ung_report').report_action(self)
        elif self.type == "bao_cao_so_du_ngan_hang":
            return self.env.ref('ccv_sql.bao_cao_so_du_ngan_hang_report').report_action(self)
        elif self.type == "danh_sach_chi_tiet_von_tu_co":
            return self.env.ref('ccv_sql.danh_sach_chi_tiet_von_tu_co_report').report_action(self)
        return super(AlphaReport, self).action_print_pdf_report()
    
    def action_print_report_tax(self):
        if self.type == 'chi_tiet_cong_no_phai_tra':
            return self.env.ref('ccv_report.chi_tiet_cong_no_phai_tra_tax_trong_nuoc_report_ccv_report').report_action(self)
        return super(AlphaReport, self).action_print_report_tax()
    