from odoo import api, fields, models, _

class ApprovalRequestNote(models.Model):
    _name = 'approval.request.note'
    _description = 'Approval Request Note'
    
    approval_request_id = fields.Many2one('approval.request', string="Approval Request")
    description = fields.Char('Description')
    quantity = fields.Float('Quantity')
    note = fields.Char('Note')
