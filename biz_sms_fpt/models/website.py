from odoo import api, fields, models, tools, http, release, registry
import base64

class Website(models.Model):
    _inherit = 'website'



    @api.model
    def _handle_favicon(self, vals):
        if vals.get('favicon'):
            favicon = vals['favicon']
            if len(vals['favicon']) < 64:
                favicon = self.favicon
            vals['favicon'] = base64.b64encode(tools.image_process(base64.b64decode(favicon), size=(256, 256), crop='center', output_format='ICO'))
