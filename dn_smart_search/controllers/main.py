from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class SmartSearchController(http.Controller):
    
    @http.route("/smart/search", type="json", auth="user")
    def dn_smart_search(self, keyword, limit=20):
        results = request.env["smart.search"].search(keyword, limit=limit)
        return {"results": results}
