from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date
import ast

import logging
_logger = logging.getLogger(__name__)

class rp_tf_vehicel_in_out_wizard(models.TransientModel):
    _name = 'rp.tf.vehicel.in.out.wizard'
    _description = 'Báo cáo sản lượng nhập xuất'

    date = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')
    department_id = fields.Many2one('hr.department',string="Phòng ban")
    type = fields.Selection([('in', 'Nhập'), ('out', 'Xuất')], string='Loại')
    is_next_day_fall_vehicle = fields.Boolean(string='Xe rớt', help="Khi tích vào, báo cáo sê in theo xe rớt ")

    # Thông tin Người Ký Tên
    voter_id = fields.Many2one(
        'res.users',
        string='Người Lập Biểu',
        default=lambda self: self.env.user,
        help="Người lập hoặc chuẩn bị báo cáo này."
    )
    loading_id = fields.Many2one(
        'res.users',
        string='Bộ nhận bốc xếp',
        help="Người đại diện cho Bộ nhận bốc xếp ký xác nhận."
    )
    stocker_id = fields.Many2one(
        'res.users',
        string='Quản lý sản xuất',
        help="Người đại diện cho Quản lý sản xuất ký xác nhận."
    )
    hr_admin_department_id = fields.Many2one(
        'res.users',
        string='Phòng HCNS',
        help="Người đại diện cho Phòng HCNS ký xác nhận."
    )
    chief_finance_id = fields.Many2one(
        'res.users',
        string='Phòng Kế toán',
        help="Người đại diện cho Kế Toán ký xác nhận."
    )
    director_id = fields.Many2one(
        'res.users',
        string='Thủ trưởng đơn vị',
        help="Người đại diện cho Thủ trưởng đơn vị ký xác nhận."
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super(rp_tf_vehicel_in_out_wizard, self).default_get(fields_list)
        ctx = self.env.context
        active_id = ctx.get("active_id")
        active_model = ctx.get("active_model")
        today = date.today()
        if active_model == "sale.vehicle.in.out":
            today = self.env["sale.vehicle.in.out"].browse(active_id).date

        env_params = self.env['ir.config_parameter'].sudo()
        chief_finance_id = env_params.get_param('ccv_bao_cao.chief_accountant_id', False)
        hr_admin_department_id = env_params.get_param('ccv_bao_cao.hr_admin_department_id', False)
        director_id = env_params.get_param('ccv_bao_cao.director_id', False)
        stocker_id = env_params.get_param('ccv_bao_cao.stocker_id', False)
        
        defaults.update({
            'date': today,
            'date_to': today,
            'voter_id': self.env.user.id,
            'chief_finance_id': int(chief_finance_id) if chief_finance_id else False,
            'hr_admin_department_id': int(hr_admin_department_id) if hr_admin_department_id else False,
            'stocker_id': int(stocker_id) if stocker_id else False,
            'director_id': int(director_id) if director_id else False,
        })
        return defaults

    @api.onchange('department_id')
    def _onchange_department_ids(self):
        for rec in self:
            if rec.department_id:
                rec.loading_id = self.env['hr.employee'].search([('department_id', '=', rec.department_id.id)], limit=1).parent_id.user_id

    def action_generate_report(self):
        return self.env.ref('ccv_api_connector.bao_cao_san_luong_nhap_xuat_report').report_action(self)

    def action_print_report(self):
        return self.env.ref('ccv_api_connector.view_rp_internal_tf_materials_wizard_action').sudo().read()[0]
