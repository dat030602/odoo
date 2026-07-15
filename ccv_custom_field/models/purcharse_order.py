from odoo import models, fields, api
import logging
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)


class purcharse_order(models.Model):
    _inherit = "purchase.order"

    description = fields.Text(string="Diễn giải")

    def write(self, vals):
        res = super(purcharse_order, self).write(vals)
        if 'description' in vals:
            for rec in self:
                if rec.picking_ids:
                    rec.picking_ids.write({'reason_output_input_stock': vals['description']})
        return res

    @staticmethod
    def html_to_text(html_content):
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n").strip()

    # @api.depends('picking_ids.reason_output_input_stock')
    # def _compute_description_picking_ids(self):
    #     for rec in self:
    #         description = ''
    #         if rec.picking_ids:
    #             reasons = [reason for reason in rec.picking_ids.mapped('reason_output_input_stock') if isinstance(reason, str)]
    #             description = '\n'.join([self.html_to_text(reason) for reason in reasons]) if reasons else ''
    #         rec.description = description

    def action_view_stock_move(self):
        return {
            'name': 'Dịch chuyển tồn kho',
            'res_model': 'stock.move',
            'view_mode': 'tree', 
            'target': 'current',
            'type': 'ir.actions.act_window',
            'views': [[self.env.ref('stock.view_move_tree').id, "tree"]],
            'domain' : [('id','in',self.picking_ids.mapped('move_ids').ids)]
        }
