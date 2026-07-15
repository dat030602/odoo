from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleReport(models.Model):
    _inherit = "sale.report"

    delivery_status = fields.Selection(string="Trạng thái giao", selection=[
        ('pending','Chưa giao'),
        ('started','Đã bắt đầu'),
        ('partial','Đã giao một phần'),
        ('full','Đã giao hết'),
    ])
    commitment_date = fields.Datetime(string="Ngày giao hàng")
    effective_date = fields.Datetime(string="Ngày hiệu lực")

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['delivery_status'] = "s.delivery_status"
        res['commitment_date'] = "s.commitment_date"
        res['effective_date'] = "s.effective_date"
        return res

    # def _group_by_sale(self):
    #     res = super()._group_by_sale()
    #     res += """,
    #         s.is_delivered"""
    #     return res
