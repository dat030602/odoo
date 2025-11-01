# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api, _
from odoo.osv import expression


class VATProductTemplate(models.Model):
    _name = 'vat.product.template'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'VAT Product Template'
    _order = "qty_available desc"

    @tools.ormcache()
    def _get_default_uom_id(self):
        # Deletion forbidden (at least through unlink)
        return self.env.ref('uom.product_uom_unit')
    
    
    @api.depends('company_id')
    def _compute_currency_id(self):
        main_company = self.env['res.company']._get_main_company()
        for template in self:
            template.currency_id = template.company_id.sudo().currency_id.id or main_company.currency_id.id

    name = fields.Char('Name', index=True, required=True, translate=True)
    price = fields.Float('Sales Price', default=1.0,digits='Product Price',
        help="Price at which the product is sold to customers.", tracking=True)
    qty_available = fields.Float('Quantity On Hand', digits='Product Unit of Measure', tracking=True,
        help="Current quantity of products.")
    vat_code = fields.Char('VAT Code')
    taxes_ids = fields.Many2many('einvoice.tax', 'vat_product_taxes_rel', 'vat_prod_id', 'tax_id', help="Default taxes used when selling the product.", 
        string='Customer Taxes')
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', default=_get_default_uom_id, required=True,
        help="Default unit of measure used for all stock operations.")
    src_product_ids = fields.Many2many('product.product', 'product_vat_product_rel', 'vat_product_id', 'product_id', string='Internal Product Reference')
    active = fields.Boolean('Active', default=True, help="If unchecked, it will allow you to hide the product without removing it.")
    currency_id = fields.Many2one('res.currency', 'Currency', compute='_compute_currency_id')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env['res.company']._company_default_get('account.move'))

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|',('name', operator, name), ('vat_code', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def name_get(self):
        # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
        self.browse(self.ids).read(['name', 'vat_code'])
        return [(vat_prod.id, '%s%s' % (vat_prod.vat_code and '[%s] ' % vat_prod.vat_code or '', vat_prod.name))
                for vat_prod in self]