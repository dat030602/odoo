# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import http, _
from odoo.http import request
from odoo.modules.module import get_resource_path
from odoo.osv import expression
from odoo.tools import pdf, split_every
from odoo.tools.misc import file_open


class CreateInvoiceController(http.Controller):

    @http.route('/get_id_create_invoice_wizard', type='json', auth='user')
    def get_id_create_invoice_wizard(self):
        return request.env.ref('biz_client_ccv.create_invoice_wizard_form_view').id