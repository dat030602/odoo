# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo.addons.web.controllers.binary import Binary
from odoo import http
from odoo.http import request
from odoo.tools import file_open, file_path, replace_exceptions
import base64
import os

class Binary(Binary):

    # --------------------------------------------------------------------------
    # Public Pages
    # --------------------------------------------------------------------------

    @http.route(['/web/sign/get_fonts', '/web/sign/get_fonts/<string:fontname>'], type='json', auth='public')
    def get_fonts(self, fontname=None):
        supported_exts = ('.ttf', '.otf', '.woff', '.woff2')
        fonts = super(Binary, self).get_fonts(fontname=fontname)
        fonts_directory = file_path(os.path.join('biz_sign', 'static', 'fonts', 'sign'))
        
        if fontname:
            font_path = os.path.join(fonts_directory, fontname)
            with file_open(font_path, 'rb', filter_ext=supported_exts) as font_file:
                font = base64.b64encode(font_file.read())
                fonts.append(font)
        else:
            font_filenames = sorted([fn for fn in os.listdir(fonts_directory) if fn.endswith(supported_exts)])
            for filename in font_filenames:
                font_file = file_open(os.path.join(fonts_directory, filename), 'rb', filter_ext=supported_exts)
                font = base64.b64encode(font_file.read())
                fonts.append(font)

        return fonts




   