# -*- coding: utf-8 -*-
from odoo import models, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import base64
import io
from urllib.request import Request, urlopen

cols = {
    'chi_tieu':0,
    'ma_so':1,
    'thuyet_minh':2,
    'nam_nay':3,
    'nam_truoc':4,
}
def col_num_to_letter(col_num):
    col_letter = ""
    while col_num >= 0:
        col_letter = chr(col_num % 26 + 65) + col_letter
        col_num = col_num // 26 - 1
    return col_letter

def int_to_roman(num):
    # Định nghĩa các giá trị La Mã
    val = [
        1000, 900, 500, 400,
        100, 90, 50, 40,
        10, 9, 5, 4,
        1
    ]
    # Ký hiệu La Mã tương ứng
    syms = [
        "M", "CM", "D", "CD",
        "C", "XC", "L", "XL",
        "X", "IX", "V", "IV",
        "I"
    ]
    
    roman_numeral = ""
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_numeral += syms[i]
            num -= val[i]
        i += 1
    return roman_numeral

class rp_payslip_salary_payment(models.AbstractModel):
    _name = 'report.biz_ccv_payslip.rp_payslip_salary_payment'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'rp_payslip_salary_payment'
    
    def generate_xlsx_report(self, workbook, data, details):
        self = self.with_context(lang=self.env.user.lang)
        company = self.env.company

        table_border_header = {
            'font_name': 'Times New Roman', 'font_size': 12,
            'align': 'center', 'border': True, 'bold': True, 'text_wrap': True,
            'color': "black"
        }
        table_border_body = {
            'font_name': 'Times New Roman', 
            'font_size': 12,
            'align': 'left', 'border': True
        }
        def get_format(*arguments):
            normal_style = {'font_name': 'Times New Roman', 'font_size': 12, 'valign':'vcenter', 'align': 'left'}
            for arg in arguments:
                normal_style.update(arg)
            return workbook.add_format(normal_style)


        for o in details:
            cols, departments = self.get_cols(o)
            luong_phep = cols.pop('luong_phep')
            luong_le = cols.pop('luong_le')
            phucap = cols.pop('phucap')
            phucap_2 = cols.pop('phucap_2')
            giamtru = cols.pop('giamtru')

            max_col = 5 + len(luong_le) + len(luong_phep) + len(phucap) + len(phucap_2) + len(giamtru) + 8

            stt_col = {
                'stt': 0,
                'ma_nv': 1,
                'ten_nv': 2,
                'chuc_danh': 3,
                'xep_loai': 4,
                'luong_cb': 5
            }
            sheet = workbook.add_worksheet(_('Salary payment %s') % o.id)
            sheet.set_column(0, 0, 5)
            sheet.set_column(1, 1, 22)
            sheet.set_column(2, 2, 40)
            sheet.set_column(3, 3, 32)
            sheet.set_column(4, 4, 10)
            sheet.set_column(5, 5, 20)
            sheet.set_column(6, 99, 10)


            y_offset = 0
            
            sheet.write(y_offset, 0, company.name, get_format({'bold': True}))
            y_offset +=1
            
            sheet.write(y_offset, 0, self.get_company_address(company), get_format({'bold': True}))
            y_offset += 2
            
            sheet.merge_range(y_offset, 0, y_offset, max_col, 'THANH TOÁN LƯƠNG %s' % o.name,get_format({'align': 'center', 'bold': True}))
            y_offset += 1
            
            sheet.write(y_offset, 4, 'Số ngày công tháng: %s' % o.working_days_per_month, get_format({'bold': True}))
            y_offset +=1

            # HEADER
            sheet.set_row(y_offset, 30)
            sheet.set_row(y_offset +1 , 30)

            sheet.merge_range(y_offset, 0, y_offset+1, 0, 'STT', get_format(table_border_header))
            sheet.merge_range(y_offset, 1, y_offset+1, 1, 'Mã nhân viên', get_format(table_border_header))
            sheet.merge_range(y_offset, 2, y_offset+1, 2, 'Họ và tên', get_format(table_border_header))
            sheet.merge_range(y_offset, 3, y_offset+1, 3, 'Chức danh', get_format(table_border_header))
            sheet.merge_range(y_offset, 4, y_offset+1, 4, 'Xếp loại', get_format(table_border_header))
            sheet.merge_range(y_offset, 5, y_offset+1, 5, 'Lương CB\n(đóng BH)', get_format(table_border_header))
            col_pc = 5
            if phucap:
                col_pc = col_pc + 1
                if len(phucap) > 1:
                    sheet.merge_range(y_offset, col_pc, y_offset, col_pc + len(phucap) - 1, 'Phụ cấp không đóng bảo hiểm', get_format(table_border_header))
                else:
                    sheet.write(y_offset, col_pc, 'Phụ cấp không đóng bảo hiểm', get_format(table_border_header))

                for i, pc in enumerate(phucap):
                    col_key = 'pc_%s' % pc
                    stt_col[col_key] = col_pc + i
                    sheet.write(y_offset+1, col_pc + i, phucap[pc], get_format(table_border_header))

                col_pc = col_pc + len(phucap) - 1

            stt_col.update({
                'tongthunhap': col_pc +1,
                'ngay_cong': col_pc + 2,
                'tyle': col_pc + 3,
                'luong_nc': col_pc + 4,
                'tang_ca_thuong': col_pc + 5,
                'thanhtien': col_pc + 6,
            })
            sheet.merge_range(y_offset, col_pc + 1, y_offset+1, col_pc + 1, 'Tổng thu nhập', get_format(table_border_header))
            sheet.merge_range(y_offset, col_pc + 2, y_offset+1, col_pc + 2, 'Ngày công', get_format(table_border_header))
            sheet.merge_range(y_offset, col_pc + 3, y_offset+1, col_pc + 3, 'Tỷ lệ', get_format(table_border_header))
            sheet.merge_range(y_offset, col_pc + 4, y_offset+1, col_pc + 4, 'Lương ngày\ncông', get_format(table_border_header))
            sheet.merge_range(y_offset, col_pc + 5, y_offset+1, col_pc + 5, 'Giờ tăng ca thường', get_format(table_border_header))
            sheet.merge_range(y_offset, col_pc + 6, y_offset+1, col_pc + 6, 'Thành tiền', get_format(table_border_header))

            col_pc = col_pc + 6
            if luong_phep:
                col_pc = col_pc + 1
                if len(luong_phep) > 1:
                    sheet.merge_range(y_offset, col_pc, y_offset, col_pc + len(luong_phep) - 1, 'Lương phép', get_format(table_border_header))
                else:
                    sheet.write(y_offset, col_pc, 'Lương phép', get_format(table_border_header))

                for i, lp in enumerate(luong_phep):
                    col_key = 'lp_%s' % lp
                    stt_col[col_key] = col_pc + i
                    sheet.write(y_offset +1, col_pc + i, luong_phep[lp], get_format(table_border_header))

                col_pc = col_pc + len(luong_phep) - 1

            if luong_le:
                col_pc = col_pc + 1
                if len(luong_le) > 1:
                    sheet.merge_range(y_offset, col_pc, y_offset, col_pc + len(luong_le) - 1, 'Lương lễ', get_format(table_border_header))
                else:
                    sheet.write(y_offset, col_pc, 'Lương lễ', get_format(table_border_header))

                for i, ll in enumerate(luong_le):
                    col_key = 'll_%s' % ll
                    stt_col[col_key] = col_pc + i
                    sheet.write(y_offset+1, col_pc + i, luong_le[ll], get_format(table_border_header))

                col_pc = col_pc + len(luong_le) - 1

            if phucap_2:
                col_pc = col_pc + 1
                if len(phucap_2) > 1:
                    for i, pc in enumerate(phucap_2):
                        pc2 = 'pc2_%s' % pc
                        stt_col[pc2] = col_pc + i
                        sheet.merge_range(y_offset, col_pc + i,y_offset +1, col_pc + i, phucap_2[pc], get_format(table_border_header))
                else:
                    pc2 = 'pc2_%s' % phucap_2[0].id
                    stt_col[pc2] = col_pc
                    sheet.merge_range(y_offset, col_pc , phucap_2[0].name, get_format(table_border_header))

                col_pc = col_pc + len(phucap_2) - 1

            if giamtru:
                col_pc = col_pc + 1
                if len(giamtru) > 1:
                    sheet.merge_range(y_offset, col_pc, y_offset, col_pc + len(giamtru) - 1, 'Các khoản giảm trừ vào lương', get_format(table_border_header))
                else:
                    sheet.write(y_offset, col_pc, 'Các khoản giảm trừ vào lương', get_format(table_border_header))

                for i, pc in enumerate(giamtru):
                    gt = 'gt_%s' % pc
                    stt_col[gt] = col_pc +  i
                    sheet.write(y_offset +1, col_pc + i, giamtru[pc], get_format(table_border_header))

                col_pc = col_pc + len(giamtru) - 1

            stt_col.update({
                'thuclinh': col_pc +1,
                'ghichu': col_pc + 2
            })
            sheet.merge_range(y_offset, col_pc + 1, y_offset +1, col_pc + 1, 'Thực lĩnh', get_format(table_border_header))
            sheet.merge_range(y_offset, col_pc + 2, y_offset +1, col_pc + 2, 'Ghi chú', get_format(table_border_header))

            y_offset += 2
            for sumkey, index in stt_col.items():
                sheet.write(y_offset, index, index, get_format(table_border_header))

            y_offset +=1

            # BODY
            stt = 0
            stt_dep = 0
            first = y_offset + 1
            for dep, employee_ids in departments.items():
                stt_dep += 1
                sheet.write(y_offset, 0, int_to_roman(stt_dep), get_format(table_border_body, {'align': 'center', 'bold': True}))
                sheet.write(y_offset, 1, dep.name, get_format(table_border_body, {'align': 'center', 'bold': True}))
                for i in range(2, max_col + 1):
                    sheet.write(y_offset, i, '', get_format(table_border_body, {'align': 'center', 'bold': True}))

                y_offset += 1
                for employee_id, vals in employee_ids.items():
                    stt += 1
                    stt_use = []
                    for key, val in vals.items():
                        format_col = get_format(table_border_body, {'align': 'right', 'num_format': '#,##'})
                        if key == 'stt':
                            format_col = get_format(table_border_body, {'align': 'center'})
                            val = stt
                        elif key in ['ma_nv','ten_nv','chuc_danh','xep_loai','ghichu']:
                            format_col = get_format(table_border_body)

                        if key in stt_col:
                            sheet.write(y_offset, stt_col[key], val, format_col)
                            stt_use.append(key)

                    for sk, index in stt_col.items():
                        if sk not in stt_use:
                            sheet.write(y_offset, index, '', get_format(table_border_body))

                    y_offset += 1

            last = y_offset
            for sumkey, index in stt_col.items():
                value = ''
                format_col = get_format(table_border_body)
                if sumkey == 'stt':
                    sheet.write(y_offset, index, '', format_col)

                elif sumkey in ['ten_nv','chuc_danh','xep_loai','ghichu']:
                    sheet.write(y_offset, index, '', format_col)

                elif sumkey == 'ma_nv':
                    format_col = get_format(table_border_body,{'bold': True})
                    sheet.write(y_offset, index, 'Tổng cộng', format_col)
                else:
                    format_col = get_format(table_border_body,{'align': 'right','bold': True, 'num_format': '#,##'})
                    col_letter = col_num_to_letter(index)
                    formula = 'sum(%s%s:%s%s)' % (col_letter, first, col_letter, last)
                    sheet.write_formula(y_offset, index, "{=%s}" % formula, format_col)

            y_offset +=1
            sheet.merge_range(y_offset, max_col - 5, y_offset ,max_col - 2, datetime.now().strftime('Ngày %d tháng %m năm %Y'), get_format({'bold': True, 'align': 'center'}))
            y_offset +=1
            sheet.write(y_offset, 0, 'NGƯỜI LẬP', get_format({'bold': True}))
            sheet.merge_range(y_offset, max_col - 5, y_offset ,max_col - 2, 'Tổng giám đốc', get_format({'bold': True, 'align': 'center'}))
            y_offset += 10
            sheet.write(y_offset, 0, o.env.user.name, get_format({'bold': True}))

    def get_cols(self, o):
        phucap = {}
        phucap_2 = {}
        giamtru = {}
        luong_phep = {}
        luong_le = {}
        departments = {}

        categ_data = self.fetch_data_employee_by_code(o)

        for slip in o.slip_ids:
            emp = slip.employee_id
            dep = emp.department_id

            categ_emp = categ_data.get(emp.id, {})
            gr_dep = departments.setdefault(dep, {})
            gr_emp = gr_dep.setdefault(emp, {
                'stt': 1,
                'ma_nv': emp.code,
                'ten_nv': emp.name,
                'chuc_danh': emp.job_title,
                'xep_loai': '',
                'luong_cb': categ_emp.get("BASIC", 0),
                'tongthunhap': categ_emp.get("TTN", 0),
                'ngay_cong': categ_emp.get("NC", 0),
                'tyle': '',
                'luong_nc': categ_emp.get("LNC", 0),
                'tang_ca_thuong': categ_emp.get("GTCT", 0),
                'thanhtien': categ_emp.get("TTCNLT", 0),
                'ot_cn': categ_emp.get("GTTCNLT", 0),
                'thanhtien_2': categ_emp.get("TTTCT", 0),
                'thuclinh': categ_emp.get("NET", 0),
                'ghichu': ''
            })

            for line in slip.line_ids:
                if line.category_id.code == 'NCLP':
                    luong_phep.setdefault(line.code, line.name)
                    
                    pc = 'lp_%s' % line.code
                    gr_emp[pc] = line.total

                elif line.category_id.code == 'NCLL':
                    luong_le.setdefault(line.code, line.name)
                    
                    pc = 'll_%s' % line.code
                    gr_emp[pc] = line.total

                elif line.category_id.code == 'PCKĐBH':
                    phucap.setdefault(line.code, line.name)
                    
                    pc = 'pc_%s' % line.code
                    gr_emp[pc] = line.total

                elif line.category_id.code == 'PC':
                    phucap_2.setdefault(line.code, line.name)
                    
                    pc = 'pc2_%s' % line.code
                    gr_emp[pc] = line.total

                elif line.category_id.code in ['DED','BH']:
                    giamtru.setdefault(line.code, line.name)
                    
                    pc = 'gt_%s' % line.code
                    gr_emp[pc] = line.total

        cols = {
            'stt': 0,
            'ma_nv': 1,
            'ten_nv': 2,
            'chuc_danh': 3,
            'xep_loai': 4,
            'luong_cb': 5,
            'phucap': phucap,
            'tongthunhap': 'Tổng thu nhập',
            'ngay_cong': 'Ngày công',
            'tyle': 'Tỷ lệ',
            'luong_nc': 'Lương ngày công',
            'tang_ca_thuong': 'Giờ tăng ca thường',
            'thanhtien': 'Thành tiền',
            'ot_cn': "Giờ tăng ca chủ nhật" ,
            'thanhtien_2': 'Thành tiền',
            'luong_phep': luong_phep,
            'luong_le': luong_le,
            'phucap_2': phucap_2,
            'giamtru': giamtru,
            'thuclinh': 'Thực lĩnh',
        } 
        return cols, departments

    def fetch_data_employee_by_code(self, o):
        query = """
        select hp.employee_id, hpl.code, sum(hpl.total) as total
        from hr_payslip hp
            join hr_payslip_run hpr on hpr.id = hp.payslip_run_id
            join hr_payslip_line hpl on hp.id = hpl.slip_id

        where hpr.id = %s
        group by hp.employee_id, hpl.code
            
        """ % o.id

        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        result = {}
        for res in query_result:
            emp = result.setdefault(res['employee_id'], {})
            if res['code'] not in emp:
                emp[res['code']] = res['total'] 
            else:
                emp[res['code']] += res['total']

        return result

    def get_company_address(self, company):
        address = ''
        if company:
            if company.street:
                address += company.street
            if company.street2:
                address += len(address) > 0 and ', ' + company.street2 or company.street2
            if company.city:
                address += len(address) > 0 and ', ' + company.city or company.city
            if company.state_id:
                address += len(address) > 0 and ', ' + company.state_id.name or company.state_id.name
            if company.country_id:
                address += len(address) > 0 and ', ' + company.country_id.name or company.country_id.name
        return address