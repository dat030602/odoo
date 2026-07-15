from odoo import models, fields
import logging
import datetime

_logger = logging.getLogger(__name__)


class StockReport(models.Model):
    _name = "stock.ccv.report"

    name = fields.Char(string="Tên báo cáo")
    date_from = fields.Date(string="Ngày bắt đầu")
    date_to = fields.Date(string="Ngày kết thúc")
    location_ids = fields.Many2many("stock.location", string="Kho")
    user_ids = fields.Many2many('stock.ccv.report.participant', string="Người tham dự")
    type = fields.Selection(
        string="Loại",
        selection=[
            ("bao_cao_xuat_nhap_ton", "Báo cáo xuất nhập tồn"),
            ("bien_ban_kiem_ke", "Biên bản kiểm kê"),
        ],
        required=True,
    )
    stock_move_state = fields.Selection(
        string="Trạng thái dịch chuyển",
        selection=[
            ("all", "Tất cả"),
            ("done", "Hoàn thành"),
            ("not_done", "Chưa hoàn thành"),
        ],
        default="done"
    )

    line1_ids = fields.One2many("stock.ccv.report.line1", "parent_id", string="Chi tiết")
    line2_ids = fields.One2many("stock.ccv.report.line2", "parent_id", string="Lịch sử")

    product_ids = fields.Many2many("product.product", string="Sản phẩm")

    def action_print(self):
        data = getattr(self,'generate_prepare_value_' + self.type)()
        return self.env.ref("ccv_bao_cao_ton_kho.%s_report" % self.type).report_action(None, data=data)

    def action_query(self):
        func = "get_data_" + self.type
        getattr(self, func)()
    
    def generate_prepare_value_bao_cao_xuat_nhap_ton(self):
        return {
            "date_from"         : self.date_from.strftime('%d/%m/%Y'),
            "date_to"           : self.date_to.strftime('%d/%m/%Y'),
            "inventories"       : ','.join(self.location_ids.mapped('display_name')) if len(self.location_ids) == 1 else "Tất cả",
            "data"              : getattr(self, "get_data_export_" + self.type)(),
        }

    def action_open_detail(self):
        self.ensure_one()
        lines = []
        context = {'default_state': 'done'}
        if self.type == "bao_cao_xuat_nhap_ton":
            title = "Báo cáo xuất nhập tồn"
            model_name = "stock.ccv.report.line1"
            if self.line1_ids:
                lines = [('id','in',self.line1_ids.ids)]
        elif self.type == "bien_ban_kiem_ke":
            title = "Biên bản kiểm kê"
            model_name = "stock.ccv.report.line2"
            if self.line2_ids:
                lines = [('id','in',self.line2_ids.ids)]
        if len(self.location_ids) > 1:
            context.update({'default_group_by_location_ids':1})
        return {
            "name": title,
            "res_model": model_name,
            "view_mode": "tree,form",
            "target": "current",
            "type": "ir.actions.act_window",
            "context": context,
            "domain": lines,
        }

    def convert_hour(self, date: datetime.datetime):
        return "%s Giờ %s Ngày %s tháng %s năm %s" % (date.hour, date.minute, date.day, date.month, date.year)

    def convert_date(self, today: datetime.date):
        return "Ngày %s tháng %s năm %s" % (today.day, today.month, today.year)

    def convert_print(self, value):
        if not value:
            return ''
        if str(value).find('202') > -1:
            return str(value).split('-')[2] + '/' + str(value).split('-')[1] + '/' + str(value).split('-')[0]
        return value

    def convert_vnd(self, amount):
        a = format(amount, ',.0f')
        return a

    def convert_usd(self, amount):
        a = format(amount, ',.2f')
        return a

    def convert_number(self, amount):
        number = str(round(amount, 3))
        if number.find('.') > -1:
            number = number.split('.')
            head = number[0]
            tail = number[1]
            if len(tail) == 1:
                number = head + '.' + tail + '00'
            elif len(tail) == 2:
                number = head + '.' + tail + '0'
            else:
                number = head + '.' + tail
        else:
            number = number + '.000'
        return number

    def get_data_bao_cao_xuat_nhap_ton(self):
        state = ['done']
        if self.stock_move_state == 'all':
            state += ['draft', 'cancel', 'waiting', 'confirmed', 'partially_available', 'assigned']
        if self.stock_move_state == 'not_done':
            state = ['draft', 'cancel', 'waiting', 'confirmed', 'partially_available', 'assigned']

        # Chuyển đổi date_from và date_to sang datetime
        date_from = datetime.datetime.combine(self.date_from, datetime.time.min) + datetime.timedelta(hours=7) # 07:00:00
        date_to = datetime.datetime.combine(self.date_to, datetime.time.max) + datetime.timedelta(hours=7)  # 16:59:59
        location_ids = self.location_ids
        if not self.location_ids:
            location_ids = self.env['stock.location'].search([])

        if self.product_ids:
            product_ids = self.product_ids.ids
        else:
            product_ids = self.env['stock.move'].search([
                '&',
                '|',
                ('location_id', 'in', location_ids.ids),
                ('location_dest_id', 'in', location_ids.ids),
                ('date', '<=', date_to)
            ]).mapped('product_id').ids

        query = "select * from function_bao_cao_xuat_nhap_ton(%s, %s, %s, %s, %s, %s)"
        self.env.cr.execute(
            query,
            (
                date_from,
                date_to,
                state,
                location_ids.ids,
                product_ids,
                self.id,
            ),
        )
        self._compute_stock_quant()
        self.line1_ids._compute_is_out()
        self.line1_ids._compute_quantity()
        return
    
    def _compute_stock_quant(self):
        lines = self.env['stock.ccv.report.line1']
        if self.type == 'bao_cao_xuat_nhap_ton':
            lines = self.line1_ids
        location_ids = self.location_ids
        if not self.location_ids:
            location_ids = self.env['stock.location'].search([])
        if not lines:
            return
        for location_id in location_ids:
            line_ids = lines.filtered(lambda l:l.location_origin_id.id == location_id.id)
            product_ids = line_ids.mapped('product_id')
            for product_id in product_ids:
                cur_lines = line_ids.filtered(lambda l:l.product_id.id == product_id.id)
                quant = cur_lines[0].stock_quant_qty
                cur_lines -= cur_lines[0]
                for line in cur_lines:
                    if location_id.id == line.location_id.id:
                        quant -= line.qty_done
                    else:
                        quant += line.qty_done
                    line.stock_quant_qty = quant

    def get_data_export_bao_cao_xuat_nhap_ton(self):
        sum_to_qty_done       = sum(self.line1_ids.mapped("to_qty_done"))
        sum_from_qty_done       = sum(self.line1_ids.mapped("from_qty_done"))
        sum_quant          = 0

        lines = []
        line_count = 0
        for location_id in self.location_ids:
            line_ids = self.sudo().line1_ids.filtered(lambda l:l.location_origin_id.id == location_id.id)
            if line_ids:
                product_ids = line_ids.mapped('product_id')
                for product_id in product_ids:
                    if line_count == 0:
                        vals = {
                                "location_origin_id"  : location_id.display_name,
                                "no"                  : -1,
                            }
                        lines.append(vals)
                        line_count += 1
                    count = 0
                    for data in line_ids.filtered(lambda l: l.product_id.id == product_id.id):
                        if count == 0:
                            vals = {
                                "location_origin_id"  : product_id.display_name,
                                "no"                  : count,
                            }
                            lines.append(vals)
                            count += 1
                        date                    = data.date                          if data.date             else ""
                        picking_id              = data.picking_id.display_name       if data.picking_id       else ""
                        ref                     = data.ref                           if data.ref              else ""
                        location_name           = data.location_id.display_name      if data.location_id      else ""
                        location_dest_id        = data.location_dest_id.display_name if data.location_dest_id else ""
                        origin                  = data.origin                        if data.origin           else ""
                        to_qty_done             = data.to_qty_done
                        from_qty_done           = data.from_qty_done
                        stock_quant_qty         = data.stock_quant_qty

                        vals = {
                            "no"                  : count,
                            "date"                : date,
                            "picking_id"          : picking_id,
                            "ref"                 : ref,
                            "location_id"         : location_name,
                            "location_dest_id"    : location_dest_id,
                            "origin"              : origin,
                            "to_qty_done"         : round(to_qty_done,3),
                            "from_qty_done"       : round(from_qty_done,3),
                            "stock_quant_qty"     : round(stock_quant_qty,3),
                        }
                        count += 1
                        lines.append(vals)
                    vals = {
                            "location_origin_id"  : "%s - %s" % (location_id.display_name, product_id.display_name),
                            "no"                  : "sum",
                            "to_qty_done"         : round(sum(line_ids.filtered(lambda l: l.product_id.id == product_id.id).mapped('to_qty_done')), 3),
                            "from_qty_done"       : round(sum(line_ids.filtered(lambda l: l.product_id.id == product_id.id).mapped('from_qty_done')), 3),
                            "stock_quant_qty"     : round(line_ids.filtered(lambda l: l.product_id.id == product_id.id)[-1].stock_quant_qty, 3),
                        }
                    sum_quant += line_ids.filtered(lambda l: l.product_id.id == product_id.id)[-1].stock_quant_qty
                    lines.append(vals)
        return {
            "sum": {
                "sum_to_qty_done"  : round(sum_to_qty_done,3),
                "sum_from_qty_done": round(sum_from_qty_done,3),
                "sum_quant"        : round(sum_quant,3),
            },
            "lines": lines,
        }
