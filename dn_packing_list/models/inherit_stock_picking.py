from odoo import models, fields

class PackingListInheritStock(models.Model):
    _inherit = 'stock.picking'

    packing_list_id = fields.Many2one('packing.list', string='Packing List', copy=False,)

    def has_return_picking(self):
        """True if at least one non-cancelled return picking exists."""
        self.ensure_one()
        return bool(self.return_ids.filtered(lambda p: p.state != 'cancel'))