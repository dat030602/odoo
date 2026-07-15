# -*- coding: utf-8 -*-
from datetime import datetime, time
import pytz

from odoo import fields, models, _
from odoo.exceptions import ValidationError


class AuditlogLineReportWizard(models.TransientModel):
    _name = "ccv.auditlog.line.report.wizard"
    _description = "Wizard Export Audit Log Line"

    date_from = fields.Date(string="Từ ngày", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="Đến ngày", required=True, default=fields.Date.context_today)

    def _build_domain(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise ValidationError(_("Từ ngày phải nhỏ hơn hoặc bằng Đến ngày."))

        user_tz_name = self.env.user.tz or "UTC"
        try:
            user_tz = pytz.timezone(user_tz_name)
        except pytz.UnknownTimeZoneError:
            user_tz = pytz.UTC

        local_dt_from = user_tz.localize(datetime.combine(self.date_from, time.min))
        local_dt_to = user_tz.localize(datetime.combine(self.date_to, time.max))
        dt_from = local_dt_from.astimezone(pytz.UTC).replace(tzinfo=None)
        dt_to = local_dt_to.astimezone(pytz.UTC).replace(tzinfo=None)
        return [("create_date", ">=", dt_from), ("create_date", "<=", dt_to)]

    def action_export_xlsx(self):
        self.ensure_one()
        return self.env.ref("ccv_auditlog_line_report_xlsx.report_auditlog_line_xlsx_wizard").report_action(self)
