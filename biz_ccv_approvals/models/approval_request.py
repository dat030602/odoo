from odoo import api, fields, models, _

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'
    
    request_note_ids = fields.One2many('approval.request.note', 'approval_request_id', string="Approval Request Note")