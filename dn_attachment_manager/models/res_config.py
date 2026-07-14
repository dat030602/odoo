from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    large_file_threshold_mb = fields.Integer(string='Large file threshold (MB)', default=20)

    def get_values(self):
        res = super().get_values()
        IrConfig = self.env['ir.config_parameter'].sudo()
        res.update(large_file_threshold_mb=int(IrConfig.get_param('dn_attachment_manager.large_file_threshold_mb', default=20)))
        return res

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param('dn_attachment_manager.large_file_threshold_mb', self.large_file_threshold_mb or 20)
