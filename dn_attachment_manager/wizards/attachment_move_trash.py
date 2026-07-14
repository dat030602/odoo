from odoo import api, fields, models


class AttachmentMoveTrash(models.TransientModel):
    _name = 'attachment.move.trash'
    _description = 'Move Attachments to Trash'

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    expire_days = fields.Integer(string='Expire after (days)', default=30)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids') or []
        if 'attachment_ids' in fields_list:
            res['attachment_ids'] = [(6, 0, active_ids)]
        return res

    def action_move(self):
        attachments = self.attachment_ids
        if attachments:
            attachments.action_move_to_trash(days=self.expire_days)
        return {'type': 'ir.actions.act_window_close'}
