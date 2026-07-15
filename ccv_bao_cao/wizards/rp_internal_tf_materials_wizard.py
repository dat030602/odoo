from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date
import ast

import logging
_logger = logging.getLogger(__name__)

class RpInternalTfMaterialsMizard(models.TransientModel):
    _name = 'rp.internal.tf.materials.wizard'
    _description = 'Sổ Chi tiết Thay thế, Sửa chữa'

    date_from = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')
    warehouse_ids = fields.Many2many('stock.warehouse',string="Kho")
    partner_ids = fields.Many2many('res.partner',string="Máy móc thiết bị")

    # Thông tin Người Ký Tên
    voter_id = fields.Many2one(
        'res.users',
        string='Người Lập Biểu',
        default=lambda self: self.env.user,
        help="Người lập hoặc chuẩn bị báo cáo này."
    )
    stocker_id = fields.Many2one(
        'res.users',
        string='Thủ Kho',
        help="Người đại diện cho Thủ Kho ký xác nhận."
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
        string='Ban Lãnh đạo',
        help="Người đại diện cho Ban Lãnh đạo ký xác nhận."
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super(RpInternalTfMaterialsMizard, self).default_get(fields_list)

        today = date.today()

        env_params = self.env['ir.config_parameter'].sudo()
        chief_finance_id = env_params.get_param('ccv_bao_cao.chief_accountant_id', False)
        hr_admin_department_id = env_params.get_param('ccv_bao_cao.hr_admin_department_id', False)
        director_id = env_params.get_param('ccv_bao_cao.director_id', False)
        stocker_id = env_params.get_param('ccv_bao_cao.stocker_id', False)
        warehouse_vtdc = env_params.get_param('ccv_bao_cao.warehouse_vtdc', [])
        warehouse_vtdc = ast.literal_eval(env_params.get_param('ccv_bao_cao.warehouse_vtdc', '[]'))
        
        defaults.update({
            'date_from': today,
            'date_to': today,
            'voter_id': self.env.user.id,
            'chief_finance_id': int(chief_finance_id) if chief_finance_id else False,
            'hr_admin_department_id': int(hr_admin_department_id) if hr_admin_department_id else False,
            'warehouse_ids': [(4,warehouse_vtdc_id) for warehouse_vtdc_id in warehouse_vtdc] if warehouse_vtdc else False,
            'stocker_id': int(stocker_id) if stocker_id else False,
            'director_id': int(director_id) if director_id else False,
        })
        return defaults

    def action_generate_report(self):
        return self.env.ref('ccv_bao_cao.report_rp_internal_tf_materials_report_xlsx').report_action(self)
