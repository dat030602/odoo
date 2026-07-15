from odoo import models, fields,api
import logging

_logger = logging.getLogger(__name__)

class StockReportparticipant(models.Model):
    _name = "stock.ccv.report.participant"

    name = fields.Char(string="Tên")
    job = fields.Char("Chức vụ")
    representative = fields.Char("Đại diện")
    user_id = fields.Many2one('res.users', "Người dùng")

    @api.onchange('user_id')
    def _onchange_user_id(self):
        for rec in self:
            rec.name = rec.user_id.name_without_position
    