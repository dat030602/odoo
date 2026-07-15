from odoo import models, fields, api
from odoo.exceptions import UserError
import json
import logging
import ast
import base64

_logger = logging.getLogger(__name__)

class SaleOrderLineReport(models.Model):
    _name = 'sale.order.line.report'
    _description = 'Sale Order Line Report'
    
    name = fields.Char(string="Tên")
    parent_id = fields.Many2one('sale.order.line.report', string="Dữ liệu phụ thuộc")
    
    line_ids = fields.One2many('sale.order.line.report.line', 'report_id', string='Dòng sản phẩm')
    line_count = fields.Integer(compute="_compute_line")

    attachment_ids = fields.Many2many("ir.attachment", string="Data")

    @api.depends('line_ids')
    def _compute_line(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def _prepare_data(self):
        self.env.cr.execute("""
            SELECT 
                so.date_order AS "Ngày đơn hàng",
                rp.name AS "Tên khách hàng",
                so.name AS "Số đơn hàng",
                rp.code_contact AS "Mã khách hàng",
                pt.default_code AS "Mã hàng",
                sol.name AS "Tên hàng",
                sol.product_uom_qty AS "Số lượng đặt hàng",
                sol.qty_delivered AS "Số lượng đã giao",
                (sol.price_unit * sol.product_uom_qty) AS "Giá trị đơn hàng",
                CASE 
                    WHEN so.state = 'sale' THEN 'Đã xác nhận'
                    WHEN so.state = 'done' THEN 'Hoàn thành'
                    ELSE 'Khác'
                END AS "Tình trạng",
                rp_salesperson.name AS "Tên nhân viên bán hàng"
            FROM sale_order_line sol
            JOIN sale_order so ON sol.order_id = so.id
            JOIN res_partner rp ON so.partner_id = rp.id
            LEFT JOIN res_users sales ON so.user_id = sales.id
            LEFT JOIN res_partner rp_salesperson ON sales.partner_id = rp_salesperson.id
            LEFT JOIN product_product pp ON sol.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE so.state IN ('sale', 'done');
        """)
        result = self.env.cr.fetchall()
        return result

    def action_confirm(self):
        if not self.parent_id:
            raise UserError("Cần phải có Dữ liệu nguồn !!!")
        if self.line_ids:
            self.line_ids.unlink()
        data = self._prepare_data()
        data = self._parse_data(data)
        for line in data:
            self.create_from_data(line)
        return {}

    def _parse_data(self, data):
        result = []
        for row in data:
            parsed_row = {
                "date_order": row[0],      # Ngày đơn hàng
                "customer_name": row[1],   # Tên khách hàng
                "order_number": row[2],    # Số đơn hàng
                "partner_code_contact": row[3],   # Mã khách hàng
                "product_default_code": row[4],    # Mã hàng
                "product_name": row[5],    # Tên hàng
                "quantity_ordered": row[6],  # Số lượng đặt hàng
                "quantity_delivered": row[7], # Số lượng đã giao
                "order_value": row[8],     # Giá trị đơn hàng
                "order_status": row[9],    # Trạng thái đơn hàng
                "salesperson_name": row[10] # Tên nhân viên bán hàng
            }
            result.append(parsed_row)
        return result

    def action_run_query(self):
        if not self.attachment_ids:
            raise UserError("Không có dữ liệu !!!")
        if self.line_ids:
            self.line_ids.unlink()
        for attachment in self.attachment_ids:
            file_content = base64.b64decode(attachment.datas).decode("utf-8")
            data = json.loads(file_content)
            data = self._parse_data(data)
            for line in data:
                self.create_from_data(line)
        return {}

    def action_sale_order_line_report_line(self):
        return {
            'name': 'Chi tiết dòng sản phẩm',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line.report.line',
            'view_mode': 'tree,form',
            'domain': [('report_id', '=', self.id)],
            'target': 'current',
        }

    @api.model
    def create_from_data(self, data):
        def find_record(model, domain):
            return self.env[model].sudo().search(domain, limit=1)

        def search_partner(partner_code):
            return find_record('res.partner', [('code_contact', '=', partner_code)])

        def search_sale_person(partner_code):
            return find_record('res.users', [('name', '=', partner_code)])
        def search_product(product_code):
            return find_record('product.product', [('default_code', '=', product_code)])

        partner = search_partner(data.get('partner_code_contact',False))
        product = search_product(data.get('product_default_code',False))
        sale_person = search_sale_person(data.get('salesperson_name',False))

        return self.env['sale.order.line.report.line'].create({
            "name":       data.get("product_name",""),
            "date_order": data.get("date_order",False),
            "partner_id": partner.id if partner else False,
            "product_id": product.id if product else False,
            "user_id":    sale_person.id if sale_person else False,
            "amount":     data.get("order_value",False),
            "order_name": data.get("order_number",False),
            "qty":        data.get("quantity_ordered",False),
            "qty_done":   data.get("quantity_delivered",False),
            "report_id":  self.id,
        })
