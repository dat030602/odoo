# -*- coding: utf-8 -*-

import logging
import json
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ODSController(http.Controller):

    @http.route('/ods/webhook', type='json', auth='public', csrf=False, methods=['POST'])
    def ods_webhook(self, **kwargs):
        datas = json.loads(request.httprequest.data)
        request.env['ods.webhook'].create_queue_webhook(datas)
        return {
            'success': True
        }
