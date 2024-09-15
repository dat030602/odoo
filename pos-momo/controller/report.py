# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http, _
from odoo.http import request
from urllib.parse import unquote
import logging
_logger = logging.getLogger(__name__)
class ReportController(http.Controller):

    @http.route(['/report/barcode', '/report/barcode/<barcode_type>/<path:value>'], type='http', auth="public")
    def report_barcode(self, barcode_type=None, value=None, **kwargs):
        """Controller able to render barcode images thanks to reportlab."""
        decoded_value = value.replace('_', '/')
        try:
            barcode = request.env['ir.actions.report'].barcode(barcode_type, decoded_value, **kwargs)
        except (ValueError, AttributeError):
            raise http.HttpResponseNotFound(_('Cannot convert into barcode.'))

        return request.make_response(barcode, headers=[('Content-Type', 'image/png')])