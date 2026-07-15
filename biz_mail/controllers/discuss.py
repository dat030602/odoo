# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo.addons.mail.controllers.discuss import DiscussController
from odoo import http
from odoo.http import request



class DiscussController(DiscussController):

    # --------------------------------------------------------------------------
    # Public Pages
    # --------------------------------------------------------------------------

    @http.route('/mail/message/post', methods=['POST'], type='json', auth='public')
    def mail_message_post(self, thread_model, thread_id, post_data, **kwargs):
        if 'is_forward' in post_data and post_data.get('is_forward'):
            request.update_context(is_forward=True)

        if 'partner_ids' in post_data:
            index = 0
            for partner in post_data['partner_ids']:
                if partner is False:
                    post_data['partner_ids'].pop(index)
                index += 1

        return super(DiscussController, self).mail_message_post(thread_model, thread_id, post_data, **kwargs)




   