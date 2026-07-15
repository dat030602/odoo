from odoo import models, fields, api
from odoo.fields import Command
from odoo.exceptions import UserError
import datetime
from collections import defaultdict
from odoo.osv.expression import AND
import logging
import re
_logger = logging.getLogger(__name__)

def extract_orders_v2(text):
    results = []
    lines = text.strip().split('\n')

    for line in lines:
        # Xử lý mẫu có dạng: <Tên>-<Mã đơn hàng>-<Khối lượng>
        if '-' in line and 'DH' in line:
            parts = line.split('-')
            order = ''
            weight = 0.0
            for part in parts:
                if 'DH' in part:
                    order_match = re.search(r'(DH\d+)', part)
                    if order_match:
                        order = order_match.group(1)
                if 'Tấn' in part or re.match(r'\d+[.,]?\d*', part.strip()):
                    try:
                        weight = float(part.strip().replace(' Tấn', '').replace(',', '.'))
                    except:
                        pass

        else:
            # Mẫu dạng tab hoặc khoảng trắng: Tên    Mã đơn hàng   Khối lượng
            columns = re.split(r'\s{2,}|\t+', line.strip())
            order = ''
            weight = 0.0
            for col in columns:
                if 'DH' in col:
                    order_match = re.search(r'(DH\d+)', col)
                    if order_match:
                        order = order_match.group(1)
                elif re.match(r'^\d+[.,]?\d*$', col.strip()):
                    try:
                        weight = float(col.strip().replace(',', '.'))
                    except:
                        pass

        if order:
            results.append({
                'order': order,
                'weight': weight
            })

    return results

class ReportStockOrderWizard(models.TransientModel):
    _name = 'report.stock.order.ccv'
    _description = 'Báo cáo hàng tồn kho khu vực'

    name  = fields.Char(string='Tên')
    
    warehouse_ids = fields.Many2many("stock.warehouse", string="Kho")
    voter_id = fields.Many2one('res.users',string="Người lập")
    team_sale_id = fields.Many2one('res.users',string="Trưởng khu vực")
    chief_finance_id = fields.Many2one('res.users',string="Phòng Kế toán")
    lead_sale_id = fields.Many2one('res.users',string="Phòng Kinh doanh")
    director_id = fields.Many2one('res.users',string="Thủ trưởng đơn vị")
    active  = fields.Boolean(default=True)
    team_id = fields.Many2one("crm.team", string="Đội bán hàng")
    
    line_ids  = fields.One2many('report.stock.order.line.ccv','parent_id',string="Chi tiết", readonly=True)
    
    @api.model
    def default_get(self, fields_list):
        defaults = super(ReportStockOrderWizard, self).default_get(fields_list)

        env_params = self.env['ir.config_parameter'].sudo()
        chief_finance_id = env_params.get_param('ccv_bao_cao.chief_accountant_id', False)
        director_id = env_params.get_param('ccv_bao_cao.director_id', False)
        lead_sale_id = env_params.get_param('ccv_bao_cao_cong_no.lead_sale_id', False)
        
        defaults.update({
            'voter_id': self.env.user.id,
            'chief_finance_id': int(chief_finance_id) if chief_finance_id else False,
            'lead_sale_id': int(lead_sale_id) if lead_sale_id else False,
            'director_id': int(director_id) if director_id else False,
        })
        
        team = self.env['crm.team'].sudo().search([
            '|', '|',
            ('user_id','=',self.sudo().env.user.id),
            ('member_ids','in',[self.sudo().env.user.id]),
            ('sales_assistant_ids','in',[self.sudo().env.user.id]),
        ], limit=1)
        
        if team:
            defaults.update({
                'team_sale_id': team.user_id.id,
                'team_id': team.id,
            })
        
        return defaults
    
    @api.onchange('team_id')
    def _onchange_team_id(self):
        for rec in self:
            rec.team_sale_id = rec.team_id.user_id
    
    def _get_product_inventory_case_1(self):
        self.ensure_one()
        if not self.warehouse_ids:
            return []

        result = []
        for warehouse in self.warehouse_ids:
            product_run_ids = self.env['product.product']
            quants = self.env['stock.quant'].search([
                ('quantity', '>', 0),
                ('location_id', '=', warehouse.lot_stock_id.id),
            ])

            for quant in quants:
                product = quant.product_id
                location = quant.location_id
                quantity = quant.quantity

                # Lấy các stock.move đã done, đến location này
                sms = self.env['stock.move'].search([
                    ('state', '=', 'done'),
                    ('product_id', '=', product.id),
                    ('location_dest_id', '=', location.id),
                ], order='date desc')

                if not sms:
                    continue

                quantity_in_sms = 0.0
                for sm in sms:
                    production_id = sm.raw_material_production_id or sm.production_id
                    picking_id = sm.picking_id
                    if (production_id and not production_id.sale_ids) or (not (production_id or picking_id)):
                        quantity_in_sms += sm.quantity_done
                    else:
                        break

                if quantity_in_sms >= quantity:
                    productions = [
                        sm.raw_material_production_id or sm.production_id
                        for sm in sms
                        if (sm.raw_material_production_id or sm.production_id)
                        and not (sm.raw_material_production_id or sm.production_id).sale_ids
                    ]

                    # Tìm LSX gần nhất có ngày
                    production_id = max(
                        [p for p in productions if p.stock_date_receipt],
                        key=lambda p: p.stock_date_receipt,
                        default=productions[0] if productions else None
                    )

                    product_run_ids |= product
                    if production_id:
                        result.append(Command.create({
                            'name': f'{production_id.name} - Dự trữ {product.display_name}',
                            'product_id': product.id,
                            'quantity': quantity,
                            'date_proc': production_id.stock_date_receipt.date() if production_id.stock_date_receipt else None,
                            'picking_type_id': production_id.picking_type_id.id,
                            'note': 'Dự trữ',
                        }))
                    else:
                        result.append(Command.create({
                            'name': f'Dự trữ {product.display_name}',
                            'product_id': product.id,
                            'quantity': quantity,
                            'note': 'Dự trữ',
                        }))


        return result

    def _get_product_inventory_case_2(self, product_run_ids):
        self.ensure_one()
        if not self.warehouse_ids:
            return []

        result = []
        stock_env = self.env

        for warehouse in self.warehouse_ids:
            # 1. Bắt đầu từ tồn kho thực tế của từng sản phẩm
            quants = stock_env['stock.quant'].search([
                ('quantity', '>', 0),
                ('location_id', '=', warehouse.lot_stock_id.id),
            ])

            for quant in quants:
                product = quant.product_id
                if product in product_run_ids:
                    continue

                real_qty_in_stock = quant.quantity
                # Biến để theo dõi lượng tồn kho đã được phân bổ
                allocated_stock = 0.0

                # 2. Tìm tất cả các Đơn hàng chưa giao đủ liên quan đến sản phẩm
                # Lấy tất cả LSX đã hoàn thành của sản phẩm
                mrp_prods = stock_env['mrp.production'].search([
                    ('product_id', '=', product.id),
                    ('state', '=', 'done'),
                ])
                # Từ đó lấy ra danh sách các Đơn hàng duy nhất
                related_orders = mrp_prods.mapped('sale_ids').filtered(lambda l:l.state not in ('cancel','draft'))

                # Sắp xếp các đơn hàng theo ngày tạo cũ nhất trước
                for order in related_orders.sorted(key=lambda r: r.date_order):
                    # Nếu đã phân bổ hết tồn kho thì dừng lại
                    if allocated_stock >= real_qty_in_stock:
                        break

                    lines = order.order_line.filtered(lambda l: l.product_id == product)
                    qty_ordered = sum(lines.mapped('product_uom_qty'))
                    qty_delivered = sum(lines.mapped('qty_delivered'))
                    
                    # Lượng hàng còn thiếu cho đơn hàng này
                    needed_quantity = qty_ordered - qty_delivered

                    # Chỉ xử lý các đơn hàng còn thiếu hàng
                    if needed_quantity > 0.01:
                        # Lượng tồn kho còn lại có thể phân bổ
                        available_stock_to_allocate = real_qty_in_stock - allocated_stock
                        
                        # Lượng phân bổ thực tế là số nhỏ hơn giữa lượng cần và lượng có
                        actual_allocation = min(needed_quantity, available_stock_to_allocate)

                        if actual_allocation > 0:
                            # Tìm LSX gần nhất liên quan đến đơn hàng này để lấy thông tin
                            first_mrp = mrp_prods.filtered(lambda m: order in m.sale_ids and m.stock_date_receipt)
                            first_mrp = sorted(first_mrp, key=lambda m: m.stock_date_receipt, reverse=True)
                            
                            result.append(Command.create({
                                'name': f'Phân bổ cho SO {order.name}',
                                'product_id': product.id,
                                'order_id': order.id,
                                'partner_id': order.partner_id.id,
                                'team_id': order.team_id.id,
                                'quantity': actual_allocation, # Số lượng phân bổ thực tế
                                'date_proc': first_mrp[0].stock_date_receipt.date() if first_mrp else None,
                                'picking_type_id': first_mrp[0].picking_type_id.id if first_mrp else False,
                                'note': f'Đơn hàng cần {needed_quantity:.2f}, phân bổ {actual_allocation:.2f} từ tồn kho',
                            }))
                            # Cập nhật lượng đã phân bổ
                            allocated_stock += actual_allocation

                # 4. Sau khi duyệt hết các đơn hàng, nếu còn tồn kho -> đưa vào "Dự trữ"
                remaining_stock_for_reserve = real_qty_in_stock - allocated_stock
                if remaining_stock_for_reserve > 0.01:
                    # Tìm LSX gần nhất không có đơn hàng để lấy thông tin ngày
                    latest_mrp_for_reserve = mrp_prods.filtered(lambda m: not m.sale_ids and m.stock_date_receipt)
                    latest_mrp_for_reserve = sorted(latest_mrp_for_reserve, key=lambda m: m.stock_date_receipt, reverse=True)

                    result.append(Command.create({
                        'name': f'Dự trữ {product.display_name}',
                        'product_id': product.id,
                        'quantity': remaining_stock_for_reserve,
                        'date_proc': latest_mrp_for_reserve[0].stock_date_receipt.date() if latest_mrp_for_reserve else None,
                        'picking_type_id': latest_mrp_for_reserve[0].picking_type_id.id if latest_mrp_for_reserve else False,
                        'note': 'Hàng tồn kho chưa phân bổ',
                    }))

        return result

    def _get_product_inventory(self):
        self.ensure_one()
        result = []

        # Trường hợp 1: lấy product_run_ids từ case_1
        product_run_ids = self.env['product.product']
        result_case_1 = self._get_product_inventory_case_1()
        for rec in result_case_1:
            product = self.env['product.product'].browse(rec[2]['product_id']) if rec and len(rec) > 2 else False
            if product:
                product_run_ids |= product

        result.extend(result_case_1)

        # Trường hợp 2: truyền product_run_ids vào
        result_case_2 = self._get_product_inventory_case_2(product_run_ids)
        result.extend(result_case_2)

        return result

    def action_get_data(self):
        self.ensure_one()
        self.line_ids.unlink()
        data = self._get_product_inventory()
        if not data:
            return
        self.write({'line_ids': data})
    
    def action_generate_report(self):
        return self.env.ref('ccv_report_stock_order.stock_order_report').report_action(self)
    
    def action_view_tree(self):
        self.ensure_one()
        action = self.env.ref('ccv_report_stock_order.view_report_stock_order_line_ccv_action').sudo().read()[0]
        action.update({
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id},
        })
        return action

