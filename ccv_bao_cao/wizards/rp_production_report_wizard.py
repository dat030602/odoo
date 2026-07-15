from odoo import models, fields, api
from odoo.exceptions import UserError
import datetime

class RpProductionReportfWizard(models.TransientModel):
    _name = 'rp.production.report.wizard'
    _description = 'Generate Production Report Wizard'
    _order = 'date_from desc' # Ví dụ: Sắp xếp theo ngày tạo giảm dần

    # Thông tin Dữ liệu Báo cáo
    date_from = fields.Date(
        string='Từ Ngày',
        required=True,
    )
    date_to = fields.Date(
        string='Đến Ngày',
        required=True,
    )
    picking_type_ids = fields.Many2many(
        'stock.picking.type',
        string='Loại hoạt đông',
        help="Chọn các loại vận chuyển cụ thể để đưa vào báo cáo. Để trống để lấy tất cả.",
        domain=[("code", "=", "mrp_operation")],
    )
    
    # Thông tin Người Ký Tên
    voter_id = fields.Many2one(
        'res.users',
        string='Người Lập Biểu',
        default=lambda self: self.env.user,
        help="Người lập hoặc chuẩn bị báo cáo này."
    )
    factory_team_leader_id = fields.Many2one(
        'res.users',
        string='Tổ Trưởng Nhà Máy',
        help="Người đại diện cho Tổ Trưởng Nhà Máy ký xác nhận."
    )
    finished_goods_warehouse_keeper_id = fields.Many2one(
        'res.users',
        string='Thủ Kho Thành Phẩm',
        help="Người đại diện cho Thủ Kho Thành Phẩm ký xác nhận."
    )
    hr_admin_department_id = fields.Many2one(
        'res.users',
        string='Phòng HCNS',
        help="Người đại diện cho Phòng Hành chính - Nhân sự ký xác nhận."
    )
    chief_finance_id = fields.Many2one(
        'res.users',
        string='Kế Toán Trưởng',
        help="Người đại diện cho Kế Toán Trưởng ký xác nhận."
    )
    director_id = fields.Many2one(
        'res.users',
        string='Ban Lãnh đạo',
        help="Người đại diện cho Ban Lãnh đạo ký xác nhận."
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise UserError("Ngày 'Từ Ngày' không được sau ngày 'Đến Ngày'.")

    @api.model
    def default_get(self, fields_list):
        defaults = super(RpProductionReportfWizard, self).default_get(fields_list)

        today = datetime.date.today()

        env_params = self.env['ir.config_parameter'].sudo()
        chief_finance_id = env_params.get_param('ccv_bao_cao.chief_accountant_id', False)
        hr_admin_department_id = env_params.get_param('ccv_bao_cao.hr_admin_department_id', False)
        director_id = env_params.get_param('ccv_bao_cao.director_id', False)
        finished_goods_warehouse_keeper_id = env_params.get_param('ccv_bao_cao.finished_goods_warehouse_keeper_id', False)

        defaults.update({
            'date_from': today,
            'date_to': today,
            'voter_id': self.env.user.id,
            'hr_admin_department_id': int(hr_admin_department_id) if hr_admin_department_id else False,
            'chief_finance_id': int(chief_finance_id) if chief_finance_id else False,
            'director_id': int(director_id) if director_id else False,
            'finished_goods_warehouse_keeper_id': int(finished_goods_warehouse_keeper_id) if finished_goods_warehouse_keeper_id else False,
        })
        return defaults
    
    @api.onchange('picking_type_ids')
    def _onchange_picking_type_ids(self):
        for rec in self:
            if rec.picking_type_ids:
                rec.factory_team_leader_id = rec.picking_type_ids[-1].user_id
            else:
                rec.factory_team_leader_id = False

    def action_generate_report(self):
        return self.env.ref('ccv_bao_cao.report_rp_production_report_xlsx').report_action(self)
