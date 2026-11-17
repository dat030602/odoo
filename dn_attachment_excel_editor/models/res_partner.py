from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    excel_attachment_ids = fields.Many2many(
        'ir.attachment',
        'res_partner_excel_attachment_rel',
        'partner_id',
        'attachment_id',
        string='Attachments',
        help="Attach Excel (.xlsx) files; click to open and edit directly.",
    )
