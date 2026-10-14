# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AddToPackingListWizard(models.TransientModel):
    _name = "add.to.packing.list.wizard"
    _description = 'Wizard Add to Packing list'

    name = fields.Char(string="Name")
    partner_id = fields.Many2one('res.partner', string="Customer")
    order_ids = fields.Many2many('sale.order', string="Order")
    order_line_ids = fields.Many2many('sale.order.line', string="Sale Order Lines",compute="_compute_order_line_wizard_ids")
    order_line_wizard_ids = fields.One2many('add.to.packing.list.wizard.line', 'add_order_id' , string="Order Line IDs")
    target_packing_list = fields.Many2one('packing.list', string="Target Packing List")

    @api.depends('order_line_wizard_ids')
    def _compute_order_line_wizard_ids(self):
        for record in self:
            if record.order_line_wizard_ids:
                order_line_ids = []
                for order_line_id in record.order_line_wizard_ids:
                    if order_line_id.order_line_id:
                        order_line_ids.append(order_line_id.order_line_id.id)
                    else:
                        order_line_ids.append(False)
                record.order_line_ids = [(6, 0, order_line_ids)]

    def confirm_form(self):
        if len(self.order_line_wizard_ids) == 0:
            raise ValidationError("No order line has been selected !")
        
        new_packing_list = False
        target = self.target_packing_list

        if not self.target_packing_list:
            shipping_id = self.order_ids[:1].partner_shipping_id.id if self.order_ids else self.partner_id.id
            new_packing_list = self.env['packing.list'].create({
                'customer': self.partner_id.id,
                'title': self.name or "New Packing List",
                'delivery_address': shipping_id,
                "active": True
            })
            target = new_packing_list
        if not target:
            return False        

        existingOrderIds = [order.id for order in target.orders]
        for order_id in self.order_ids:
            if order_id.id not in existingOrderIds:
                target.write({
                    'orders': [(4,order_id.id)],
                    'delivery_address': order_id.partner_shipping_id.id or self.partner_id.id
                })

        existingLineIds = [line.order_line_id.id for line in target.line_ids]
        toCreate = []
        for line in self.order_line_wizard_ids:
            if line.order_line_id.id not in existingLineIds:
                if line.order_line_id:
                    toCreate.append([0,0,{
                        'name': line.name,
                        'display_type':line.display_type,
                        'sequence': self.env['ir.sequence'].next_by_code('sequence_packing_list_line'),
                        'packing_list_id': target.id,
                        'order_ref': line.order_line_id.order_id.id,
                        'order_line_id': line.order_line_id.id,
                        'product_id': line.product_id.id,
                        'quantity':line.product_uom_qty,
                        'unit_price':line.price_unit,
                    }])
                    
                else:
                    toCreate.append([0,0,{
                        'name': line.name,
                        'display_type':line.display_type,
                        'packing_list_id': target.id,
                    }])

        if len(toCreate) > 0: 
            target.write({
                'line_ids': toCreate 
            })

        packing_list_id = new_packing_list.id if new_packing_list else target.id
        action = self.env['ir.actions.actions']._for_xml_id('dn_packing_list.packing_list_action')
        action['domain'] = [
        ('id','=', packing_list_id)
        ]
        return action

    def load_all_order_lines(self):
        self.ensure_one()
        self.order_line_wizard_ids.unlink()
        result = []
        for l in self.order_ids.order_line:
            if not l.display_type and l.packable_remaining_qty <= 0:
                continue
            qty = l.packable_remaining_qty if not l.display_type else l.product_uom_qty
            result.append({
                "order_line_id": l.id,
                'product_uom_qty': qty,
                'name': l.name,
                'price_unit': l.price_unit,
                'price_subtotal': qty * l.price_unit,
                'display_type': l.display_type,
                'add_order_id': self.id,
            })
        if result:
            self.order_line_wizard_ids.create(result)
        return {
            'view_type':'form',
            'view_mode': 'form',
            'res_model' : 'add.to.packing.list.wizard',
            'view_id': self.env.ref('dn_packing_list.add_to_packing_list_wizard_form_view').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id
        }
