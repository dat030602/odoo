# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    name = fields.Char(tracking=True)
    categ_id = fields.Many2one(tracking=True)
    default_code = fields.Char(tracking=True)
    uom_id = fields.Many2one(tracking=True)
    uom_po_id = fields.Many2one(tracking=True)

    distributor_allowed_company_ids = fields.Many2many(
        comodel_name='res.company',
        relation='product_template_res_company_rel',
        column1='product_template_id',
        column2='res_company_id'
    ) 

    check_category_id = fields.Many2one('uom.category',compute="_compute_check_category",store=True)

    default_specification_id = fields.Many2one('uom.uom','Default specification',help="Enter the specification to calculate the quantity on the printout of the stock note, based on the unit of the default specification and the available unit of the product")

    packaging_specification_id = fields.Many2one('uom.uom', string='Định mức bao bì', domain="[('category_id','=',check_category_id)]", options="{'no_create':1}", help="Chọn đơn vị tính định mức bao bì của sản phẩm")

    @api.depends('uom_id','uom_id.category_id')
    def _compute_check_category(self):
        for res in self:
            res.check_category_id = False
            if res.uom_id and res.uom_id.category_id:
                res.check_category_id = res.uom_id.category_id

    @api.constrains('distributor_allowed_company_ids')
    def _check_distributor_allowed_company_ids(self):
        for record in self:
            if len(record.distributor_allowed_company_ids) < 1:
                raise ValidationError(_("Must have 1 or more companies"))

    def _check_distributor_allowed_company(self, distributor_allowed_company_ids=False):
        for record in self:
            company_ids = record.env.user.company_ids
            base_distributor_allowed_company_ids = record.distributor_allowed_company_ids
            new_distributor_allowed_company = self.env['res.company'].browse(distributor_allowed_company_ids)

            remove_company = base_distributor_allowed_company_ids - new_distributor_allowed_company
            add_company = new_distributor_allowed_company - base_distributor_allowed_company_ids

            if remove_company:
                for company in remove_company:
                    if company not in company_ids:
                        raise UserError(_("You do not have permission to delete Company '%s'", company.name))

            if add_company:
                for company in add_company:
                    if company not in company_ids:
                        raise UserError(_("You do not have permission to add Company '%s'", company.name))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'categ_id' in fields_list:
            res.pop('categ_id', None)
        if 'uom_id' in fields_list:
            res.pop('uom_id', None)
        if 'uom_po_id' in fields_list:
            res.pop('uom_po_id', None)
        return res

    def write(self, vals):
        if 'distributor_allowed_company_ids' in vals:
            if vals.get('distributor_allowed_company_ids'):
                distributor_allowed_company_ids = vals['distributor_allowed_company_ids'][0][
                    2]  # Decode [(6, 0, [...])] command
                self._check_distributor_allowed_company(distributor_allowed_company_ids)
        res = super(ProductTemplate, self).write(vals)
        return res

