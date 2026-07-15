# -*- coding: utf-8 -*-

import json
import logging
from werkzeug.utils import redirect

from odoo import http, registry
from odoo.http import request

_logger = logging.getLogger("############### Backup ODOO DB Dropbox Logs #################")


class DropboxAuth(http.Controller):

    @http.route('/dropbox/authentication', type='http', auth="none")
    def oauth2callback(self, **kw):
        """ This route/function is called by Dropbox when user Accept/Refuse the consent of Dropbox """

        dbname = request.session.db

        with registry(dbname).cursor() as cr:
            if kw.get('code'):
                menu = request.env(cr, request.session.uid)['auto.backup'].set_all_tokens(kw['code'])
                return redirect(menu)
            else:
                return kw.get('error_description')
