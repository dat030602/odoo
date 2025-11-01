# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare


class Picking(models.Model):
    _inherit = 'stock.picking'

    is_int_trans_invoiced = fields.Boolean('Is Internal Transfer')
    viettel_sinvoice_template_id = fields.Many2one('viettel.sinvoice.template', 'S-Invoice Template')
    vehicle = fields.Char('Vehicle')
    sinvoice_ids = fields.One2many('viettel.sinvoice', 'picking_id', 'Viettel S-invoice')
    sinvoice_ref = fields.Char('S-Invoice Reference', compute='_compute_sinvoice_reference', store=False)
    sinvoice_count = fields.Integer('S-Invoices Count', compute='_compute_sinvoice_reference')

    @api.depends('sinvoice_ids')
    def _compute_sinvoice_reference(self):
        for picking in self:
            picking.sinvoice_ref = ' - '.join(sorted(picking.sinvoice_ids.filtered(lambda s: s.state not in ('draft', 'confirm')).mapped('name')))
            picking.sinvoice_count = len(picking.sinvoice_ids)

    def _prepare_sinvoice_line_values(self):
        line_vals = []
        for line in self.move_ids_without_package:
            name = line.product_id.name or ''

            val = (0, 0, {
                'name': name,
                'origin': name,
                'product_id': line.product_id.id or False,
                'price_unit': line.product_id.standard_price,
                'quantity': line.product_uom_qty,
                'discount': 0,
                'uom_id': line.product_uom.id,
                'sinvoice_line_tax_id': False,
                'selection': '1',
            })
            line_vals.append(val)
        return line_vals

    def create_data_sinvoice(self):
        if not self.viettel_sinvoice_template_id:
            raise UserError("You must select a template for invoicing !")
        sinvoice_val = {
            'picking_id': self.id,
            'viettel_sinvoice_template_id': self.viettel_sinvoice_template_id.id,
            'partner_vat_id': self.viettel_sinvoice_template_id.branch_id.partner_id.id or False,
            'company_id': self.company_id.id,
            'internal_move_type': False,
            # S-Invoice Data Information
            'invoiceIssuedDate': fields.Datetime.now(),
            'adjustmentType': '1',
            # Internal Transfer Information
            'commandOf': self.viettel_sinvoice_template_id.branch_id.partner_id.name or '',
            'commandNo': '',
            'contractNo': '',
            'commandDes': self.origin or '',
            'commandDate': fields.Datetime.now(),
            'exportAt': self.location_id.vat_description or '',
            'importAt': self.location_dest_id.vat_description or '',
            'vehicle': self.vehicle,
        }
        sinvoice_line_vals = self._prepare_sinvoice_line_values()
        sinvoice_val['sinvoice_line'] = sinvoice_line_vals
        sinvoice_id = self.env['viettel.sinvoice'].create(sinvoice_val)
        return sinvoice_id

    def action_create_data_sinvoice(self):

        sinvoice_id = self.create_data_sinvoice()
        view = self.env.ref('viettel_sinvoice.view_viettel_sinvoice_form')
        return {
            'name': _('S-Invoice'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'viettel.sinvoice',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': sinvoice_id.id,
            'context': dict(self.env.context, create=False)
        }
