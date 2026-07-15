from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class QuotationReportWizard(models.TransientModel):
    _name = 'quotation.report.wizard'
    _description = 'Wizard to generate Stock Move Report'

    date = fields.Date(string="Ngày", default=date.today(), required=True)
    partner_id = fields.Many2one("res.partner", string="Khách hàng", required=True)
    pricelist_id = fields.Many2one("product.pricelist", string="Bảng giá", required=True)
    category_ids = fields.Many2many("product.category", string="Danh mục", required=True)
    user_id = fields.Many2one("res.users", string="Nhân viên bán hàng", default=lambda self: self.env.user.id, required=True)
    bonus_price_id = fields.Many2one('sale.bonus.price.unit', string="Quỹ dự phòng")
    amount_ck = fields.Float(string="Số tiền Chiết khấu (<= 100 sẽ là tỷ lệ %)")
    amount = fields.Monetary(string="Số tiền quỹ")
    currency_id = fields.Many2one('res.currency', string="Tiền tệ", default=lambda l:l.env.user.currency_id)
    
    @api.onchange('bonus_price_id')
    def _onchange_bonus_price_id(self):
        for rec in self:
            rec.amount = rec.bonus_price_id.amount
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for rec in self:
            if rec.partner_id:
                rec.pricelist_id = rec.partner_id.property_product_pricelist.id
            else:
                rec.pricelist_id = False
            current_date = date.today()
            bonus_price_id = self.env['sale.bonus.price.unit']
            if rec.partner_id.team_id:
                bonus_price_id = bonus_price_id.search([('team_id','=',rec.partner_id.team_id.id), ('date_from','<=',current_date),('date_to','>=',current_date)],limit=1)
            rec.bonus_price_id = bonus_price_id.id
                
    def _get_pricelist_items(self):
        result = []
        item_ids = self.pricelist_id.item_ids
        if self.category_ids:
            item_ids = item_ids.filtered(lambda l:l.categ_id in self.category_ids)
        else:
            item_ids = item_ids.filtered(lambda l:l.fixed_price > 0)
        for rec in item_ids:
            product_id = rec.env['product.template'].search([('categ_id','=',rec.categ_id.id),('packaging_image','!=',False)],limit=1)
            packaging_image = product_id.packaging_image if product_id else False
            specification = 'Bao25Kg/\nBao50kg'
            name = rec.categ_id.name
            categ = rec.categ_id.parent_id.name
            fixed_price = rec.fixed_price
            if self.amount_ck != 0:
                if self.amount_ck <= 100:
                    amount = self.amount_ck / 100 * fixed_price
                else:
                    amount = self.amount_ck
                fixed_price += amount
            if rec.fixed_price and self.amount:
                fixed_price += self.amount
            price_unit_w_tax = fixed_price
            tax = fixed_price * 0.05
            price_unit = price_unit_w_tax + tax
            result.append({
                'packaging_image': packaging_image,
                'name_for_report': name,
                'categ': categ,
                'specification': specification,
                'price_unit_w_tax': price_unit_w_tax,
                'tax': tax,
                'price_unit': price_unit,
            })
        return result
                
    def get_report_docx_context(self):
        return {
            'user_id': self.user_id,
            'str_date': self.date.strftime('Ngày %d/%m/%Y'),
            'company': self.env.user.company_id,
            'partner_id': self.partner_id,
            'items': self._get_pricelist_items(),
        }

    def action_generate_report(self):
        return self.env.ref('ccv_bao_cao.action_quotation_report_docx').report_action(self)
