# -*- coding: utf-8 -*-
{
    "name": "CCV Audit Log Line XLSX Report",
    "version": "16.0.1.0.0",
    "category": "Tools",
    "summary": "Export audit log lines to Excel",
    "images": ["static/description/icon.png"],
    "depends": ["auditlog", "report_xlsx"],
    "data": [
        "security/ir.model.access.csv",
        "report/auditlog_line_report.xml",
        "views/auditlog_line_report_wizard_views.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
