# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

# ========= HAS UPDATE TO ODOO 16 =========

import json
import mimetypes

from werkzeug import exceptions
from werkzeug.urls import url_decode

from odoo import http
from odoo.http import request, content_disposition, serialize_exception as _serialize_exception
from odoo.tools.misc import html_escape

from odoo.addons.web.controllers import report


class ReportController(report.ReportController):
    @http.route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        if converter != "py3o":
            return super(ReportController, self).report_routes(
                reportname=reportname, docids=docids, converter=converter, **data
            )
        context = dict(request.env.context)

        if docids:
            docids = [int(i) for i in docids.split(",")]
        if data.get("options"):
            data.update(json.loads(data.pop("options")))
        if data.get("context"):
            # Ignore 'lang' here, because the context in data is the
            # one from the webclient *but* if the user explicitely wants to
            # change the lang, this mechanism overwrites it.
            data["context"] = json.loads(data["context"])
            if data["context"].get("lang"):
                del data["context"]["lang"]
            context.update(data["context"])

        report = request.env["ir.actions.report"]._get_report_from_name(reportname)
        if not report:
            raise exceptions.HTTPException(
                description="Py3o action report not found for report_name "
                            "%s" % reportname)

        res, filetype = report._render(report.id, docids, data)
        filename = report.gen_report_download_filename(docids, data)
        if not filename.endswith(filetype):
            filename = "{}.{}".format(filename, filetype)
        content_type = mimetypes.guess_type("x." + filetype)[0]
        http_headers = [
            ("Content-Type", content_type),
            ("Content-Length", len(res)),
            ("Content-Disposition", content_disposition(filename)),
        ]
        return request.make_response(res, headers=http_headers)

    @http.route()
    def report_download(self, data, context=None, token=None):
        """This function is used by 'py3oactionmanager.js' in order to trigger the download of
        a pdf/controller report.

        :param data: a javascript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with an attachment header

        """
        requestcontent = json.loads(data)
        url, report_type = requestcontent[0], requestcontent[1]
        try:
            if report_type == "py3o":
                reportname = url.split("/report/py3o/")[1].split("?")[0]
                docids = None
                if "/" in reportname:
                    reportname, docids = reportname.split("/")

                if docids:
                    # Generic report:
                    response = self.report_routes(
                        reportname, docids=docids, converter="py3o", context=context
                    )
                else:
                    data = list(url_decode(url.split("?")[1]).items())
                    response = self.report_routes(
                        reportname, converter="py3o", **dict(data)
                    )
                response.set_cookie("fileToken", token)
                return response
            else:
                return super(ReportController, self).report_download(data, context=context, token=token)
        except Exception as e:
            se = _serialize_exception(e)
            error = {"code": 200, "message": "Odoo Server Error", "data": se}
            return request.make_response(html_escape(json.dumps(error)))
