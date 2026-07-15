# Copyright 2020 Creu Blanca
# Copyright 2020 Ecosoft Co., Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from io import BytesIO

from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)
try:
    from PyPDF2 import PdfFileReader, PdfFileWriter
except ImportError as err:
    _logger.debug(err)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        document, ttype = super(IrActionsReport,self)._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        if res_ids and self.id == self.env.ref('biz_payslip_pdf_report.action_report_payslip_pdf').id:
            if isinstance(res_ids, int):
                res_ids = [res_ids]
            password = self._get_pdf_password(res_ids[:1])
            if password:
                document = self._encrypt_pdf(document, password)
        return document, ttype

    def _get_pdf_password(self, res_id):
        payslip = self.env['hr.payslip'].sudo().browse(res_id)
        if not payslip or not payslip.employee_id:
            return False
            
        password = payslip.employee_id.pdf_password
        if not password:
            return False

        return password

    def _encrypt_pdf(self, data, password):
        if not password:
            return data
        output_pdf = PdfFileWriter()
        in_buff = BytesIO(data)
        pdf = PdfFileReader(in_buff)
        output_pdf.appendPagesFromReader(pdf)
        output_pdf.encrypt(password)
        buff = BytesIO()
        output_pdf.write(buff)
        return buff.getvalue()

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {"encrypt"}
