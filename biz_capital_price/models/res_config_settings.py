from odoo import fields, models, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    capital_price_priority = fields.Integer("Số lần chạy ưu tiên", config_parameter="biz_capital_price.capital_price_priority")
