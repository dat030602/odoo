from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home

class WebsiteInfoBlocker(Home):

    @http.route('/website/info', type='http', auth='public', website=True)
    def block_website_info(self, **kwargs):
        return request.not_found()