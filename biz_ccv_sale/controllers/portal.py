# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request, content_disposition


class PortalAccount(http.Controller):

    # @http.route(['/video'], type='http', auth="user", website=True)
    @http.route(['/video'], type='json', auth='public', website=True, csrf=False)
    def portal_video(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        return request.render("web_widget_image_webcam.WebCamDialog",  {})

