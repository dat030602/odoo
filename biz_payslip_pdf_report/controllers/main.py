# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import re
import datetime

from PyPDF2 import PdfFileReader, PdfFileWriter

from odoo import models, _,http
from odoo.http import request, route, Controller
from odoo.tools.safe_eval import safe_eval
import zipfile
from odoo.http import request
from io import BytesIO

class HrPayroll(Controller):

    @route(["/print/payslip-pdf"], type='http', auth='user')
    def get_payroll_report_print_pdf(self, list_ids='', **post):
        if not list_ids or re.search("[^0-9|,]", list_ids):
            return request.not_found()

        ids = [int(s) for s in list_ids.split(',')]
        payslips = request.env['hr.payslip'].browse(ids)
        out_file = self._create_temp_zip(payslips)
        return http.send_file(
            filepath_or_fp=out_file,
            mimetype="application/zip",
            as_attachment=True,
            filename=_("Payslips.zip"),
        )

    def _create_temp_zip(self, payslips):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for payslip in payslips:
                report = request.env.ref('biz_payslip_pdf_report.action_report_payslip_pdf', False)
                report = report.with_context(lang=payslip.employee_id.sudo().address_home_id.lang)
                pdf_content, _ = report.sudo()._render_qweb_pdf(payslip.id, data={'company_id': payslip.company_id})
                filename = "%s.%s" % (payslip.display_name, 'pdf')
                zip_file.writestr(
                    filename,
                    pdf_content,
                )
            zip_buffer.seek(0)
            zip_file.close()
        return zip_buffer
