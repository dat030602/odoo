from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero
import datetime


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.model
    def _get_default_stock_date_receipt(self): # giống default fields date_planned_start
        if self.env.context.get('default_date_deadline'):
            return fields.Datetime.to_datetime(self.env.context.get('default_date_deadline'))
        return datetime.datetime.now()
    
    stock_date_receipt = fields.Datetime('Inventory date(used for warehouse receipts)', default=_get_default_stock_date_receipt)

    @api.onchange('date_planned_start')
    def load_stock_date_receipt(self):
        for res in self:
            stock_date_receipt = False
            if res.date_planned_start:
                stock_date_receipt = res.date_planned_start
            res.stock_date_receipt = stock_date_receipt
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'sale_order_id' in vals:
                sale_order = self.env['sale.order'].browse(int(vals.get('sale_order_id')))
                if sale_order:
                    vals['stock_date_receipt'] = sale_order.stock_date_receipt
        return super(MrpProduction, self).create(vals_list)

    def write(self, vals):
        for res in self:
            if 'stock_date_receipt' in vals:
                if res.move_raw_ids:
                    for raw in res.move_raw_ids:
                        raw._set_backdate(vals.get('stock_date_receipt'))
                if res.move_finished_ids:
                    for finish in res.move_finished_ids:
                        finish._set_backdate(vals.get('stock_date_receipt'))
        return super(MrpProduction, self).write(vals)

    def _compute_move_finished_ids(self):
        for production in self:
            if production.state != 'draft':
                updated_values = {}
                # if production.date_planned_finished:
                #     updated_values['date'] = production.date_planned_finished
                if production.date_deadline:
                    updated_values['date_deadline'] = production.date_deadline
                if 'date' in updated_values or 'date_deadline' in updated_values:
                    production.move_finished_ids = [
                        Command.update(m.id, updated_values) for m in production.move_finished_ids
                    ]
                continue
            # delete to remove existing moves from database and clear to remove new records
            production.move_finished_ids = [Command.delete(m) for m in production.move_finished_ids.ids]
            production.move_finished_ids = [Command.clear()]
            if production.product_id:
                production._create_update_move_finished()
            else:
                production.move_finished_ids = [
                    Command.delete(move.id) for move in production.move_finished_ids if move.bom_line_id
                ]

    def action_confirm(self):
        res = super(MrpProduction, self).action_confirm()
        for mrp in self:
            mrp_production_ids = mrp._get_children()
            for child in mrp_production_ids:
                child.stock_date_receipt = mrp.stock_date_receipt
                for picking in child.picking_ids:
                    picking.stock_date_receipt = child.stock_date_receipt
            if mrp.picking_ids:
                for picking in mrp.picking_ids:
                    picking.stock_date_receipt = mrp.stock_date_receipt
        return res

    def action_confirm_multi(self):
        for rec in self:
            rec.action_confirm()

    def button_mark_done_multi(self):
        for rec in self:
            if rec.stock_date_receipt:
                productions_to_do = self.env['mrp.production']
                productions_to_do |= rec

                for production in productions_to_do:
                    error_msg = ""
                    if production.product_tracking in ('lot', 'serial') and not production.lot_producing_id:
                        production.action_generate_serial()
                    if production.product_tracking == 'serial' and float_compare(production.qty_producing, 1,
                                                                                 precision_rounding=production.product_uom_id.rounding) == 1:
                        production.qty_producing = 1
                    else:
                        production.qty_producing = production.product_qty - production.qty_produced
                    production._set_qty_producing()
                    for move in production.move_raw_ids:
                        if move.state in ('done', 'cancel') or not move.product_uom_qty:
                            continue
                        rounding = move.product_uom.rounding
                        if move.has_tracking in ('serial', 'lot') and float_is_zero(move.quantity_done,
                                                                                    precision_rounding=rounding):
                            error_msg += "\n  - %s" % move.product_id.display_name

                    if error_msg:
                        error_msg = _('You need to supply Lot/Serial Number for products:') + error_msg
                        raise UserError(error_msg)

                productions_to_validate = self.env['mrp.production'].browse(rec.ids)
                # if not rec.qty_producing:
                productions_to_validate.with_context(skip_immediate=True, manual_validate_date_time=rec.stock_date_receipt).sudo().button_mark_done()


    def button_mark_done(self):
        self = self.sudo()
        for rec in self:
            if rec.env.user.has_group('to_backdate.group_backdate'):
                if not rec._context.get('manual_validate_date_time'):
                    view = rec.env.ref('biz_to_stock_backdate.mrp_production_view_validate_datetime_manual')
                    ctx = dict(rec._context or {})
                    ctx.update({'default_mrp_production_id': rec.id})
                    return {
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'mrp.production.backdate.wizard',
                        'views': [(view.id, 'form')],
                        'view_id': view.id,
                        'target': 'new',
                        'context': ctx,
                    }
                manual_validate_date_time = rec._context.get('manual_validate_date_time', False)
                for picking in self.picking_ids:
                    picking.write({'mrp_production_id': rec and rec.id})
                    if not picking.date_done:
                        picking.write({'date_done': manual_validate_date_time or False})
            return super(MrpProduction, rec.sudo()).button_mark_done()
