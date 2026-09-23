from odoo import models

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super().session_info()
        rules = self.env['dn.hide.chatter.activity.rule'].sudo().search([])
        hide_rules = {
            rule.model_name: {
                'hide_chatter': rule.hide_chatter,
                'hide_activity': rule.hide_activity,
            } for rule in rules
        }
        res['dn_hide_chatter_rules'] = hide_rules
        return res
