from odoo import models, fields, api
import logging
from datetime import datetime
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class approval_request(models.Model):
    _inherit = "approval.category"

    has_user_ids = fields.Selection(string="Nhân sự đi cùng",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    has_location_start = fields.Selection(string="Địa điểm bắt đầu",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    has_location_end = fields.Selection(string="Địa điểm kết thúc",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    has_total_km = fields.Selection(string="Tổng số Km", selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    has_fuel_start = fields.Selection(string="Tình trạng xăng/dầu lúc đi",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    has_fuel_end = fields.Selection(string="Tình trạng xăng/dầu lúc về",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    has_fuel_consumed = fields.Selection(string="Tổng số xăng/dầu tiêu thụ",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    has_fuel_rate = fields.Selection(string="Định mức",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    has_driver_id = fields.Selection(string="Lái xe",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    has_vehicle_type = fields.Selection(string="Loại xe",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    has_vehicle_plate = fields.Selection(string="Biển số",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    has_vehicle_condition_start = fields.Selection(string="Tình trạng xe lúc đi",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    has_vehicle_condition_end = fields.Selection(string="Tình trạng xe lúc về",selection=[
        ('required','Bắt buộc'),
        ('optional','Tùy chọn'),
        ('no','Không'),
    ],default="no")
    