from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date

class RpInternalTfWizard(models.TransientModel):
    _name = 'rp.internal.tf.wizard'
    _description = 'Sổ chi tiết chuyển kho'

    date_from = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')
    warehouse_ids = fields.Many2many('stock.warehouse',string="Kho")

    create_user_id = fields.Many2one('res.users',string="Người tạo phiếu")

    voter_id = fields.Many2one('res.users',string="Người lập")
    chief_trade_id = fields.Many2one('res.users', string="Phòng Thương mại")
    chief_finance_id = fields.Many2one('res.users',string="Phòng Kế toán")
    director_id  = fields.Many2one('res.users',string="Thủ trưởng đơn vị")

    @api.model
    def default_get(self, fields_list):
        defaults = super(RpInternalTfWizard, self).default_get(fields_list)

        today = date.today()

        env_params = self.env['ir.config_parameter'].sudo()
        chief_finance_id = env_params.get_param('ccv_bao_cao.chief_accountant_id', False)
        director_id = env_params.get_param('ccv_bao_cao.director_id', False)

        defaults.update({
            'date_from': today,
            'date_to': today,
            'create_user_id': self.env.user.id,
            'voter_id': self.env.user.id,
            'chief_finance_id': int(chief_finance_id) if chief_finance_id else False,
            'director_id': int(director_id) if director_id else False,
        })
        return defaults

    def action_generate_report(self):
        return self.env.ref('ccv_bao_cao.report_rp_internal_tf_wizard_xlsx').report_action(self)
