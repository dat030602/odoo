# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import http, models, tools, Command, _
from odoo.http import request, content_disposition
from odoo.addons.sign.controllers import main


class SignCustom(main.Sign):

    def get_document_qweb_context(self, sign_request_id, token, **post):
        sign_request = http.request.env['sign.request'].sudo().browse(sign_request_id).exists()
        current_request_item = sign_request.request_item_ids.filtered(lambda r: r.access_token == token)
        if not current_request_item and sign_request.access_token != token:
            http.request.env.context = dict(http.request.env.context, lang='en_US')
            return http.request.render('sign.deleted_sign_request')
        return super(SignCustom, self).get_document_qweb_context(sign_request_id, token, **post)
