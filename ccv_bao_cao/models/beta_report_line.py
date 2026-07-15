from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class BetaReportLine1(models.TransientModel):
    _name = "beta.report.line1"
    _description = "Tong Hop Cong No Phai Thu"
    _inherit = ["report.line.mixin"]
    _order = "partner_id"
    
    customer_name = fields.Char(string="Tên khách hàng", default="")
    customer_code = fields.Char(string="Mã khách hàng", default="")
    customer_group = fields.Char(string="Mã nhóm khách hàng", default="")

class BetaReportLine2(models.TransientModel):
    _name = "beta.report.line2"
    _description = "Tổng hợp công nợ phải trả"
    _inherit = ["report.line.mixin"]
    _order = "partner_id"

    customer_name = fields.Char(string="Tên nhà cung cấp", default="")
    customer_code = fields.Char(string="Mã nhà cung cấp", default="")
    address = fields.Char(string="Địa chỉ", default="")
    vat = fields.Char(string="Mã số thuế", default="")

class BetaReportLine3(models.TransientModel):
    _name = "beta.report.line3"
    _description = "Tong Hop Cong No Phai Thu USD"
    _inherit = ["report.line.mixin"]
    _order = "partner_id"
    
    customer_name = fields.Char(string="Tên khách hàng", default="")
    customer_code = fields.Char(string="Mã khách hàng", default="")
    address = fields.Char(string="Địa chỉ", default="")
    vat = fields.Char(string="Mã số thuế", default="")

class BetaReportLine4(models.TransientModel):
    _name = "beta.report.line4"
    _description = "Tổng hợp công nợ phải trả USD"
    _inherit = ["report.line.mixin"]
    _order = "partner_id"

    customer_name = fields.Char(string="Tên nhà cung cấp", default="")
    customer_code = fields.Char(string="Mã nhà cung cấp", default="")
    address = fields.Char(string="Địa chỉ", default="")
    vat = fields.Char(string="Mã số thuế", default="")

class BetaReportLine7(models.TransientModel):
    _name = "beta.report.line7"
    _description = "Danh sách chi tiền vốn tự có"
    _inherit = ["report.line.mixin"]
