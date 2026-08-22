from odoo import http
from odoo.http import request, route
import logging

_logger = logging.getLogger(__name__)


class SmartSearchController(http.Controller):

    @route("/smart/search", type="jsonrpc", auth="user")
    def dn_smart_search(self, keyword, limit=20):
        results = request.env["smart.search"].search(keyword, limit=limit)
        return {"results": results}
