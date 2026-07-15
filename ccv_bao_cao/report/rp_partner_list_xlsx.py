# -*- coding: utf-8 -*-
from odoo import models, fields, api
import xlsxwriter

class RpPartnerListXlsxReport(models.AbstractModel):
    _name = "report.ccv_bao_cao.rp_partner_list_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Partner List Report XLSX"

    def generate_xlsx_report(self, workbook, data, partners):
        sheet = workbook.add_worksheet('Danh sach lien he')
        
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center'})
        text_fmt = workbook.add_format({'border': 1, 'align': 'left', 'text_wrap': True})
        num_fmt = workbook.add_format({'border': 1, 'align': 'center'})
        
        headers = ['STT', 'Mã liên hệ', 'Tên liên hệ', 'Nhân viên kinh doanh', 'Khu vực', 'Kiểu liên hệ', 'Địa chỉ', 'Mã số thuế', 'Điện thoại/Di động', 'Email', 'Tên ngân hàng', 'Số tài khoản', 'Số hợp đồng']
        col_widths = [5, 15, 30, 20, 20, 15, 40, 15, 15, 25, 25, 20, 15]
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_fmt)
            sheet.set_column(col, col, col_widths[col])
            
        row = 1
        # Phục hồi hàm sudo() để tránh lỗi chặn quyền trên crm.team (Khu vực) và res.users
        for i, partner in enumerate(partners.sudo(), 1):
            bank_names = []
            bank_accs = []
            if partner.bank_ids:
                for b in partner.bank_ids:
                    bank_names.append(b.bank_id.name if b.bank_id else '')
                    bank_accs.append(b.acc_number or '')
            
            p_type = dict(partner._fields['company_type'].selection).get(partner.company_type, '')
            address = ', '.join(filter(bool, [partner.street, partner.street2, partner.city, partner.state_id.name, partner.country_id.name]))
            
            sheet.write(row, 0, i, num_fmt)
            sheet.write(row, 1, partner.ref or '', text_fmt)
            sheet.write(row, 2, partner.name or '', text_fmt)
            sheet.write(row, 3, partner.user_id.name if partner.user_id else '', text_fmt)
            sheet.write(row, 4, partner.team_id.name if getattr(partner, 'team_id', False) else '', text_fmt)
            sheet.write(row, 5, p_type, text_fmt)
            sheet.write(row, 6, address, text_fmt)
            sheet.write(row, 7, partner.vat or '', text_fmt)
            phone = partner.phone or partner.mobile or ''
            if partner.phone and partner.mobile and partner.phone != partner.mobile:
                phone = f"{partner.phone} / {partner.mobile}"
            sheet.write(row, 8, phone, text_fmt)
            sheet.write(row, 9, partner.email or '', text_fmt)
            sheet.write(row, 10, '\n'.join(bank_names), text_fmt)
            sheet.write(row, 11, '\n'.join(bank_accs), text_fmt)
            sheet.write(row, 12, getattr(partner, 'contract_number', ''), text_fmt)
            row += 1
