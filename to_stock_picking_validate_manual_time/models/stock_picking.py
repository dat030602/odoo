from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    mrp_production_id = fields.Many2one('mrp.production', 'Manufacturing Order', readonly=True)

    def button_validate(self):
        if not self.mrp_production_id:
            if not self._context.get('manual_validate_date_time') and self.env.user.has_group('to_backdate.group_backdate'):
                view = self.env.ref('to_stock_picking_validate_manual_time.view_validate_datetime_manual')
                ctx = dict(self._context or {})
                ctx.update({'default_picking_id': self.id})
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.picking.validate.manual.datetime.wizard',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'context': ctx,
                }
        return super(StockPicking, self).button_validate()

    def action_done(self):
        res = super(StockPicking, self).action_done()
        manual_validate_date_time = self._context.get('manual_validate_date_time', False)
        if manual_validate_date_time:
            self.filtered(lambda x: x.state == 'done').write({'date_done': manual_validate_date_time})
        return res

    def _action_done(self):
        """Call `_action_done` on the `stock.move` of the `stock.picking` in `self`.
        This method makes sure every `stock.move.line` is linked to a `stock.move` by either
        linking them to an existing one or a newly created one.

        If the context key `cancel_backorder` is present, backorders won't be created.

        :return: True
        :rtype: bool
        """
        self._check_company()
        manual_validate_date_time = self._context.get('manual_validate_date_time', False)
        todo_moves = self.move_ids.filtered(
            lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
        for picking in self:
            if picking.owner_id:
                picking.move_ids.write({'restrict_partner_id': picking.owner_id.id})
                picking.move_line_ids.write({'owner_id': picking.owner_id.id})
        todo_moves._action_done(cancel_backorder=self.env.context.get('cancel_backorder'))
        if not manual_validate_date_time:
            self.write({'date_done': fields.Datetime.now(), 'priority': '0'})

        # if incoming/internal moves make other confirmed/partially_available moves available, assign them
        done_incoming_moves = self.filtered(
            lambda p: p.picking_type_id.code in ('incoming', 'internal')).move_ids.filtered(lambda m: m.state == 'done')
        done_incoming_moves._trigger_assign()

        self._send_confirmation_email()
        return True
