from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    excel_editor_save_option = fields.Selection([
        ('ask', 'Ask every time'),
        ('overwrite', 'Always overwrite original file'),
        ('new_version', 'Always create a new version'),
    ], string='Excel Save Option', default='ask', required=True,
       help='Choose how edited Excel attachments are saved by default.')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['excel_editor_save_option']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['excel_editor_save_option']
