from odoo import models, fields, api
import logging
from datetime import datetime
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class approval_request(models.Model):
    _inherit = "approval.request"

    user_ids = fields.Many2many("res.users", string="Nhân sự đi cùng")
    location_start = fields.Char(string="Địa điểm bắt đầu")
    location_end = fields.Char(string="Địa điểm kết thúc")
    km_start = fields.Integer("Chỉ số Km lúc đi", default=0)
    km_end = fields.Integer("Chỉ số Km lúc về", default=0)
    total_km = fields.Integer("Tổng số Km", compute="_compute_total_km")
    fuel_start = fields.Char(string="Tình trạng xăng/dầu lúc đi",default="")
    fuel_end = fields.Char(string="Tình trạng xăng/dầu lúc về",default="")
    fuel_consumed = fields.Float(string="Tổng số xăng/dầu tiêu thụ")
    fuel_rate = fields.Float(string="Định mức")
    driver_id = fields.Many2one("res.users", string="Lái xe")
    vehicle_type = fields.Char(string="Loại xe")
    vehicle_plate = fields.Char(string="Biển số")
    vehicle_condition_start = fields.Char(string="Tình trạng xe lúc đi")
    vehicle_condition_end = fields.Char(string="Tình trạng xe lúc về")
    type_car = fields.Selection(string="Loại xe",selection=[
        ('1','Xe du lịch'),
        ('2', 'Xe tải/ Xe đầu kéo'),
    ],default="1")
    phone_contact = fields.Char(string="Điện thoại liên hệ")
    contact_name = fields.Char(string="Tên người liên hệ")

    has_user_ids = fields.Selection(string="Nhân sự đi cùng",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_user_ids")
    has_location_start = fields.Selection(string="Địa điểm bắt đầu",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_location_start")
    has_location_end = fields.Selection(string="Địa điểm kết thúc",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_location_end")
    has_total_km = fields.Selection(string="Tổng số Km", selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_total_km")
    has_fuel_start = fields.Selection(string="Tình trạng xăng/dầu lúc đi",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_fuel_start")
    has_fuel_end = fields.Selection(string="Tình trạng xăng/dầu lúc về",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_fuel_end")
    has_fuel_consumed = fields.Selection(string="Tổng số xăng/dầu tiêu thụ",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_fuel_consumed")
    has_fuel_rate = fields.Selection(string="Định mức",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_fuel_rate")
    has_driver_id = fields.Selection(string="Lái xe",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_driver_id")
    has_vehicle_type = fields.Selection(string="Loại xe",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_vehicle_type")
    has_vehicle_plate = fields.Selection(string="Biển số",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_vehicle_plate")
    has_vehicle_condition_start = fields.Selection(string="Tình trạng xe lúc đi",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_vehicle_condition_start")
    has_vehicle_condition_end = fields.Selection(string="Tình trạng xe lúc về",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],related="category_id.has_vehicle_condition_end")

    @api.depends('km_start','km_end')
    def _compute_total_km(self):
        for rec in self:
            rec.total_km = rec.km_end - rec.km_start
