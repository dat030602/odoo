from datetime import datetime, timedelta, date
from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def send_birthday_customer_notifications(self):
        today = date.today()
        partners = self.env["res.partner"].search(
            [
                ("fpt_date_of_birth", "!=", False),
                ("type_contact_ids.code_type_contact", "in", ['KH','NCC']),
            ]
        )

        for partner in partners:
            birthday = fields.Date.from_string(partner.fpt_date_of_birth)
            birthday_this_year = self._get_birthday_this_year(birthday, today)

            if self._is_within_birthday_window(today, birthday_this_year):
                self._send_birthday_notification(partner, today, birthday_this_year, "customer")

    def _send_birthday_notification(self, partner, today, birthday_this_year, notification_type):
        days_before = (birthday_this_year - today).days
        if notification_type == "customer":
            self._send_birthday_customer_notification(partner, birthday_this_year, days_before)
        else:
            self._send_birthday_employee_notification(partner, birthday_this_year, days_before)

    def _send_birthday_customer_notification(self, partner, birthday_this_year, days_before):
        users_to_notify = self._get_users_to_notify(partner, "customer")
        self._create_activity(partner, users_to_notify, "customer", birthday_this_year, days_before)

    def _send_birthday_employee_notification(self, partner, birthday_this_year, days_before):
        users_to_notify = self._get_users_to_notify(partner, "employee")
        self._create_activity(partner, users_to_notify, "employee", birthday_this_year, days_before)

    def _get_birthday_this_year(self, birthday, today):
        return birthday.replace(year=today.year)

    def _is_within_birthday_window(self, today, birthday_this_year):
        start_date = birthday_this_year - timedelta(days=5)
        end_date = birthday_this_year
        return today == start_date or today == end_date

    def _create_activity(self, partner, users_to_notify, notification_type, birthday_this_year, days_before):
        for user in users_to_notify:
            if notification_type == 'employee':
                partner = partner.user_id.partner_id
            birthday_this_year = birthday_this_year.strftime('%d/%m/%Y')
            if partner:
                activity_values = {
                    'res_model_id': self.env.ref('ccv_birthday_notification.model_res_partner').id,
                    "res_id": partner.id,
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "user_id": user,
                    "summary": f"Thông báo sinh nhật {partner.name}",
                    "note": f"Sinh nhật {'khách hàng' if notification_type == 'customer' else 'nhân viên'} {partner.name} vào ngày {birthday_this_year}. Chúc mừng sinh nhật!",
                }
                self.env["mail.activity"].create(activity_values)

    def _get_users_to_notify(self, partner, notification_type):
        ids = set()
        if notification_type == "customer":
            ids.update(self._get_customer_notify_users(partner))
        elif notification_type == "employee":
            ids.update(self._get_employee_notify_users(partner))
        ids.add(2)
        return ids

    def _get_customer_notify_users(self, partner):
        ids = set()
        ids.add(partner.user_id.id) if partner.user_id else None
        ids.update(partner.sales_assistant_ids.ids)
        ids.add(
            partner.sales_team_captain_id.id
        ) if partner.sales_team_captain_id else None
        ids.update(self._get_head_team_users())
        return ids

    def _get_employee_notify_users(self, partner):
        ids = set()
        ids.add(partner.user_id.id) if partner.user_id else None
        ids.add(partner.parent_id.id) if partner.parent_id else None
        ids.update(self._get_head_team_users())
        return ids

    def _get_head_team_users(self):
        if not hasattr(self, "_cached_head_team_users"):
            cached_head_team_users = (
                self.env["hr.employee"]
                .search([("department_id", "in", [3, 32])])
                .mapped("user_id")
                .ids
            )
        return cached_head_team_users

    @api.model
    def send_birthday_employee_notifications(self):
        today = date.today()
        employees = self.env["hr.employee"].search([('user_id','!=',False)])

        for employee in employees:
            birthday = self._get_employee_birthday(employee)
            if not birthday:
                continue
            birthday_this_year = self._get_birthday_this_year(birthday, today)
            if self._is_within_birthday_window(today, birthday_this_year):
                self._send_birthday_notification(employee, today, birthday_this_year, "employee")

    def _get_employee_birthday(self, employee):
        if employee.birthday:
            return fields.Date.from_string(employee.birthday)
        if employee.user_id and employee.user_id.partner_id.fpt_date_of_birth:
            return fields.Date.from_string(employee.user_id.partner_id.fpt_date_of_birth)
        return None
