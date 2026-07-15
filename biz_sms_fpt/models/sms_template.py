# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.osv import expression
from odoo.exceptions import ValidationError


class SmsTemplate(models.Model):
    _inherit = "sms.template"

    fpt_template_type = fields.Selection(selection=[
        ("order_confirmation", "Order Confirmation"),
        ("order_completion", "Order Completion"),
        ("happy_birthday", "Happy Birthday")
    ], string="SMS Template", default=False, copy=False)

    time_from_fpt = fields.Datetime(string="Time From")
    time_to_fpt = fields.Datetime(string="Time To")

    @api.onchange("fpt_template_type")
    def _onchange_model_id(self):
        if self.fpt_template_type:
            self.model_id = False
        else:
            pass

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if self._context.get("fpt_res_model") and self._context.get("fpt_res_model") in ["res.partner", "hr.employee"]:
            args = expression.AND([[("fpt_template_type", 'in', [False, "happy_birthday"])], args])
        return super(SmsTemplate, self)._name_search(name, args, operator, limit, name_get_uid)

    @api.onchange("fpt_template_type")
    def _onchange_body(self):
        if self.fpt_template_type:
            if self.fpt_template_type == "order_confirmation":
                self.body = """Đơn hàng {{object.name}} của bạn với số tiền là {{format_amount(object.amount_total, object.currency_id)}} đã được xác nhận. Đừng ngần ngại liên hệ với chúng tôi nếu bạn có bất kỳ câu hỏi nào."""
            elif self.fpt_template_type == "order_completion":
                self.body = """Đơn hàng {{object.name}} đã giao hàng thành công. Cảm ơn bạn đã tin tưởng và lựa chọn chúng tôi!."""
            else:
                self.body = """Công ty {{user.env.company.name}} xin chân thành cảm ơn anh/chị đã tin tưởng hợp tác với Công ty trong suốt thời gian qua.
Công ty chúng tôi xin chân gửi lời chúc mừng tốt đẹp nhất đến anh/chị {{object.name}} nhân ngày sinh nhật. 
Chúc anh/chị có một ngày sinh nhật thật ý nghĩa và hạnh phúc bên cạnh những người yêu thương."""
        else:
            self.body = False

    @api.constrains("fpt_template_type", "time_from_fpt", "time_to_fpt")
    def _check_time_from_and_time_to_fpt(self):
        for record in self:
            if record.fpt_template_type == "happy_birthday" and ((not record.time_from_fpt and record.time_to_fpt) or (record.time_from_fpt and not record.time_to_fpt)):
                raise ValidationError(_("Please enter the full birthday application date."))

    @api.constrains("model_id", "fpt_template_type")
    def _check_fpt_template_type_and_model_id_unique(self):
        for record in self:
            if record.fpt_template_type:
                result = self.search([("id", "!=", record.id), ("model_id", "=", record.model_id.id), ("fpt_template_type", "=", record.fpt_template_type)])
                if result:
                    raise ValidationError(_("Configure an existing message template, update the existing template instead of creating a new one."))