from odoo import models, fields

class PackingListInheritAccount(models.Model):
    _inherit = 'account.move'

    packing_list_id = fields.Many2one('packing.list', string='Packing List')
    pk_tracking_number = fields.Char(string="Tracking Number")
    pk_po_number = fields.Char(string="Customer PO Number(s)")
