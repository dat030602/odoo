from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stock_date_receipt = fields.Datetime('Inventory date(used for warehouse receipts)')
    
    @api.onchange('scheduled_date')
    def _onchange_scheduled_date(self):
        self.stock_date_receipt = self.scheduled_date

    def write(self, vals):
        for res in self:
            if 'stock_date_receipt' in vals:
                if res.move_ids:
                    for move in res.move_ids:
                        move._set_backdate(vals.get('stock_date_receipt'))
                if res.move_ids_without_package:
                    for move_package in res.move_ids_without_package:
                        move_package._set_backdate(vals.get('stock_date_receipt'))
        return super(StockPicking, self).write(vals)

    def action_confirm_multi(self):
        for rec in self:
            rec.action_confirm()

    def button_validate_backdate_multi(self):
        for rec in self:
            if rec.stock_date_receipt:
                pickings_to_do = self.env['stock.picking']
                pickings_to_do |= rec

                pickings_to_validate = self.env['stock.picking'].browse(rec.ids)
                if pickings_to_validate.show_set_qty_button:
                    for picking in pickings_to_do:
                        picking.move_ids._set_quantities_to_reservation()
                    pickings_to_validate.with_context(skip_immediate=True, manual_validate_date_time=rec.stock_date_receipt).button_validate()
                else:
                    pickings_to_validate.with_context(skip_backorder=True, manual_validate_date_time=rec.stock_date_receipt).button_validate()

    def update_date_done(self):
        for rec in self:
            if not rec.date_done and rec.state == 'done':
                state = dict(rec._fields['state']._description_selection(self.env)).get('done')
                tracking = rec.message_ids.filtered(lambda x: x.tracking_value_ids)
                if tracking:
                    for track in tracking.tracking_value_ids:
                        result = track.filtered(lambda x: x.new_value_char == state)
                        if result:
                            rec.date_done = result[0].mail_message_id.date

    # def _action_done(self):
    #     """Call `_action_done` on the `stock.move` of the `stock.picking` in `self`.
    #     This method makes sure every `stock.move.line` is linked to a `stock.move` by either
    #     linking them to an existing one or a newly created one.
    #
    #     If the context key `cancel_backorder` is present, backorders won't be created.
    #
    #     :return: True
    #     :rtype: bool
    #     """
    #     self._check_company()
    #
    #     todo_moves = self.move_ids.filtered(
    #         lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
    #     for picking in self:
    #         if picking.owner_id:
    #             picking.move_ids.write({'restrict_partner_id': picking.owner_id.id})
    #             picking.move_line_ids.write({'owner_id': picking.owner_id.id})
    #     todo_moves._action_done(cancel_backorder=self.env.context.get('cancel_backorder'))
    #     # self.write({'date_done': fields.Datetime.now(), 'priority': '0'})
    #
    #     # if incoming/internal moves make other confirmed/partially_available moves available, assign them
    #     done_incoming_moves = self.filtered(
    #         lambda p: p.picking_type_id.code in ('incoming', 'internal')).move_ids.filtered(lambda m: m.state == 'done')
    #     done_incoming_moves._trigger_assign()
    #
    #     self._send_confirmation_email()
    #     return True
