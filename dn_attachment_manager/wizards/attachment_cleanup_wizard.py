from odoo import api, fields, models


class AttachmentCleanupWizard(models.TransientModel):
    _name = 'attachment.cleanup.wizard'
    _description = 'Attachment Cleanup Wizard'

    orphan = fields.Boolean(string='Orphan', default=True)
    duplicate = fields.Boolean(string='Duplicate', default=False)
    larger_than_mb = fields.Integer(string='Larger than (MB)', default=20)
    before_date = fields.Date(string='Before Date')

    preview_count = fields.Integer(string='Preview Count', readonly=True)
    preview_size = fields.Integer(string='Preview Size (Bytes)', readonly=True)

    def _build_domain(self):
        domain = [('name', 'not like', '.js'), ('name', 'not like', '.css'), ('name', 'not like', '.scss')]
        if self.orphan:
            domain.append(('is_orphan', '=', True))
        if self.duplicate:
            domain.append(('is_duplicate', '=', True))
        if self.larger_than_mb:
            domain.append(('file_size', '>', int(self.larger_than_mb) * 1024 * 1024))
        if self.before_date:
            domain.append(('create_date', '<', self.before_date))
        return domain

    def action_preview(self):
        domain = self._build_domain()
        attachments = self.env['ir.attachment'].search(domain)
        self.preview_count = len(attachments)
        self.preview_size = sum(a.file_size or 0 for a in attachments)
        list_view = self.env.ref('dn_attachment_manager.view_attachment_list')
        return {
            'name': 'Attachments Preview',
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'views': [(list_view.id, 'list')],
            'view_id': list_view.id,
            'domain': domain,
        }

    def action_confirm_delete(self):
        domain = self._build_domain()
        attachments = self.env['ir.attachment'].search(domain)
        count = len(attachments)
        total = sum(a.file_size or 0 for a in attachments)
        if count:
            attachments.unlink()
        return {'type': 'ir.actions.act_window_close'}
