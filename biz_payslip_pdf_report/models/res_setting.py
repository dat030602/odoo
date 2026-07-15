from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_note_payslip(self):
        return """
        <p>(*) Các thu nhập phải đóng BHXH theo luật hiện hành = A.1 + A.2 + A.7
</p><p>
(**) Thuế lũy tiến theo biểu thuế TNCN hiện hành
</p><p>
(***) Các thu nhập được miễn thuế TNCN theo luật hiện hành = A4 + A5
</p><p>
(****) Thu nhập được miễn thuế TNCN một phần theo luật hiện hành = A6
        </p>

        """

    note_payslip = fields.Html('Note',default=_get_note_payslip)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    note_payslip = fields.Html('Note', related='company_id.note_payslip', readonly=False)
