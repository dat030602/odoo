from odoo import models, fields, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gemini_api_key = fields.Char(
        string='Gemini API Key',
        config_parameter='purchase_customs_ocr_ccv.gemini_api_key',
        help='API key for Google Gemini AI service',
        default='',
        groups='purchase.group_purchase_manager',
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update(
            gemini_api_key=ICP.get_param('purchase_customs_ocr_ccv.gemini_api_key', default=''),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        for record in self:
            ICP.set_param('purchase_customs_ocr_ccv.gemini_api_key', record.gemini_api_key or '')
