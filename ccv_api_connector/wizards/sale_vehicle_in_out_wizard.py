from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleVehicleInOutWizard(models.TransientModel):
    _name = "sale.vehicle.in.out.wizard"
    _description = "Vehicle In/Out Line"

    number_of_vehicle = fields.Integer(string="Số lượng xe", default=1)
    type = fields.Selection(
        string="Loại",
        selection=[
            ("in", "Nhập"),
            ("out", "Xuất"),
        ],
        default="out",
    )
    vehicle_num = fields.Char("Biển số xe")
    vehicle_driver = fields.Char("Tài xế")
    partner_name = fields.Char("Đại lý/NCC")
    quantity = fields.Float(string="Số lượng", digits="Product Unit of Measure")
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
    note = fields.Char(string="Ghi chú", copy=False)

    sale_order_ids = fields.Many2many("sale.order", string="Đơn hàng")
    purchase_order_ids = fields.Many2many("purchase.order", string="Đơn hàng")

    sale_vehicle_id = fields.Many2one("sale.vehicle.in.out")

    @api.onchange("sale_order_ids", "purchase_order_ids")
    def _onchange_partner_name(self):
        for rec in self:
            names = []
            # Lấy thông tin từ sale_order_ids
            for idx, order in enumerate(rec.sale_order_ids):
                abbr = order.abbreviation or ""
                if abbr:
                    code = (
                        order.sale_order_type_id.code
                        if order.sale_order_type_id
                        else ""
                    )
                    if idx == 0 and code and abbr:
                        name = f"{code} - {abbr}"
                    elif abbr:
                        name = f"{abbr}"
                    else:
                        name = ""
                    if name:
                        names.append(name)
            # Lấy thông tin từ purchase_order_ids
            for idx, order in enumerate(rec.purchase_order_ids):
                code = "TM"
                abbr = order.abbreviation if hasattr(order, "abbreviation") else ""
                if abbr:
                    if idx == 0 and code and abbr:
                        name = f"{code} - {abbr}"
                    elif abbr:
                        name = f"{abbr}"
                    else:
                        name = ""

                    if name:
                        names.append(name)
            if names:
                rec.partner_name = " + ".join(names)

    @api.onchange("vehicle_num")
    def _onchange_vehicle_num(self):
        if self.vehicle_num:
            import re

            # Bỏ hết các ký tự đặc biệt, chỉ lấy số và chữ
            plate = (
                self.vehicle_num.replace(" ", "")
                .replace(".", "")
                .replace(",", "")
                .replace("_", "")
                .replace("-", "")
            )
            matches = []
            # Tìm pattern: 2 số, 1 chữ, 4-5 số (cho phép 4 hoặc 5 số cuối)
            pattern = re.compile(r"(\d{2})([A-Z])(\d{5})", re.IGNORECASE)
            result = pattern.search(plate)
            if result:
                num1, char, num2 = result.groups()
                if len(num2) == 4:
                    num2 = "0" + num2
                # Không thêm dấu gạch nối
                formatted_plate = f"{num1}{char.upper()}{num2}"
                matches = [formatted_plate]
            if matches:
                self.vehicle_num = matches[0].strip()

    @api.model
    def default_get(self, fields_list):
        defaults = super(SaleVehicleInOutWizard, self).default_get(fields_list)
        defaults["uom_id"] = 28
        defaults["sale_vehicle_id"] = self.env.context.get(
            "default_sale_vehicle_in_out_id"
        )
        defaults["type"] = self.env.context.get("default_type")
        return defaults

    def action_create_vehicle(self):
        SaleVehicleInOutLine = self.env["sale.vehicle.in.out.line"]
        lines = []
        for wizard in self:
            for i in range(wizard.number_of_vehicle or 1):
                vals = {
                        "sale_vehicle_id": wizard.sale_vehicle_id._origin.id
                        if wizard.sale_vehicle_id
                        else False,
                        "type": wizard.type,
                        "vehicle_num": wizard.vehicle_num,
                        "vehicle_driver": wizard.vehicle_driver,
                        "sale_order_ids": [(6, 0, wizard.sale_order_ids.ids)]
                        if wizard.type == "out" and wizard.sale_order_ids
                        else False,
                        "purchase_order_ids": [(6, 0, wizard.purchase_order_ids.ids)]
                        if wizard.type == "in" and wizard.purchase_order_ids
                        else False,
                        "partner_name": wizard.partner_name,
                        "quantity": wizard.quantity,
                        "uom_id": wizard.uom_id._origin.id if wizard.uom_id else False,
                        "user_note": wizard.note,
                    }
                lines.append(vals)
        SaleVehicleInOutLine.create(lines)
        return {"type": "ir.actions.act_window_close"}
