from odoo import api, fields, models


class AttachmentRestoreSelected(models.TransientModel):
    _name = 'attachment.restore.selected'
    _description = 'Restore Selected Attachments'

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids') or []
        if 'attachment_ids' in fields_list:
            res['attachment_ids'] = [(6, 0, active_ids)]
        return res

    def action_restore(self):
        attachments = self.attachment_ids
        if attachments:
            attachments.action_restore()
        return {'type': 'ir.actions.act_window_close'}
