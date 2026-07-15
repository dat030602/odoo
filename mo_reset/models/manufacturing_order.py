from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_is_zero, float_compare
import logging

_logger = logging.getLogger(__name__)

class ManufacturingOrder(models.Model):
    _inherit = "mrp.production"

    def action_draft(self):
        move_ids = self.move_raw_ids + self.move_finished_ids
        svls = move_ids.stock_valuation_layer_ids.sudo()
        account_move_ids = svls.mapped('account_move_id')
        for account_move_id in account_move_ids:
            account_move_id.button_draft()
        svls.unlink()
        account_move_ids.unlink()
        move_ids.move_line_ids.write({'state': 'draft'})
        move_ids.write({'state': 'draft'})
        self.write({'state': False})
        return True

    # def unlink(self):
    #     """
    #     Unlinks MRP Production records, reverting related stock moves,
    #     stock move lines, and accounting entries to a draft state before unlinking.
    #     This method is designed to properly clean up all associated records
    #     when an MRP Production is deleted.
    #     """
    #     # Call the super method first to ensure Odoo's default unlink logic runs,
    #     # especially for security and other core functionalities, before custom logic.
    #     # This is crucial for proper inheritance.
    #     sm_to_delete = self.env['stock.move']
    #     for mrp in self:
    #         if mrp.state not in ('draft', 'cancel'):
    #             raise UserError("You cannot delete a manufacturing order that is not in draft or cancelled state.")
    #         workorders = self.env['mrp.workorder'].search([('production_id', '=', mrp.id)])
    #         if workorders:
    #             workorders.state = 'cancel'
    #             # workorders.unlink()
    #         # Search for all stock moves related to the current MRP Production.
    #         # This includes both raw material consumption moves and finished product moves.
    #         sms = self.env['stock.move'].sudo().search([
    #             '|',
    #             ('raw_material_production_id', '=', mrp.id),
    #             ('production_id', '=', mrp.id)
    #         ])

    #         sms.write({'state': 'cancel'})
    #         sms.move_line_ids.write({'state': 'cancel'})
    #         sm_to_delete |= sms
            
    #         account_move_ids = sms.stock_valuation_layer_ids.mapped('account_move_id')

    #         for account_move_id in account_move_ids:
    #             account_move_id.button_draft()
    #             account_move_id.unlink()
                

    #         sms.stock_valuation_layer_ids.unlink()
    #         mrp._compute_state()
        
    #     # Return the result of the super call.
    #     res = super(ManufacturingOrder, self).unlink()
    #     sm_to_delete.write({'state': 'cancel'})
    #     sm_to_delete.move_line_ids.write({'state': 'cancel'})
    #     sm_to_delete.unlink()
    #     return res
