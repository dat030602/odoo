import datetime
import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


def sizeof_fmt(size):
    """Human-friendly file size.

    Examples: "123 B", "12 KB", "5.3 MB", "1.2 GB"
    """
    if not size:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    val = float(size)
    while val >= 1024.0 and i < len(units) - 1:
        val /= 1024.0
        i += 1
    if units[i] == "B":
        return f"{int(val)} B"
    # show one decimal for small values, integer for larger
    if val < 10:
        return f"{val:.1f} {units[i]}"
    return f"{val:.0f} {units[i]}"


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    human_size = fields.Char(compute="_compute_size", store=True)
    is_duplicate = fields.Boolean(compute="_compute_duplicate", store=True)
    is_orphan = fields.Boolean(compute="_compute_orphan", store=True)
    checksum_count = fields.Integer(compute="_compute_duplicate", store=True)
    # Recycle bin fields
    in_trash = fields.Boolean(default=False, index=True)
    trash_date = fields.Datetime()
    trash_uid = fields.Many2one('res.users', string='Trashed By')
    expire_date = fields.Datetime()

    @api.depends("file_size")
    def _compute_size(self):
        for attachment in self:
            attachment.human_size = sizeof_fmt(attachment.file_size)

    @api.depends("checksum")
    def _compute_duplicate(self):
        # Use direct SQL aggregation for performance with large tables
        attachments_with_checksum = self.filtered(lambda a: a.checksum)
        if not attachments_with_checksum:
            for a in self:
                a.is_duplicate = False
                a.checksum_count = 0
            return

        checksums = list(set(attachments_with_checksum.mapped('checksum')))
        # Prepare placeholders for SQL IN
        params = tuple(checksums)
        sql = """
            SELECT checksum, COUNT(*)
            FROM ir_attachment
            WHERE checksum IN %s
            GROUP BY checksum
        """
        # psycopg2 accepts tuple for IN (%s)
        self.env.cr.execute(sql, (params,))
        rows = self.env.cr.fetchall()
        counts = {r[0]: r[1] for r in rows}

        for a in self:
            if a.checksum:
                cnt = counts.get(a.checksum, 0)
                a.checksum_count = cnt
                a.is_duplicate = cnt > 1
            else:
                a.checksum_count = 0
                a.is_duplicate = False

    @api.depends("res_model", "res_id")
    def _compute_orphan(self):
        # Group attachments by model and check existence with direct SQL per table
        by_model = {}
        for a in self:
            if a.res_model and a.res_id:
                by_model.setdefault(a.res_model, []).append(a)
            else:
                a.is_orphan = True

        for model_name, attachments in by_model.items():
            try:
                model = self.env[model_name]
            except Exception as e:
                _logger.error("Error occurred while checking orphan attachments for model %s: %s", model_name, e)
                # Model not found -> all attachments are orphan
                for a in attachments:
                    a.is_orphan = True
                continue

            table = model._table
            ids = list({int(a.res_id) for a in attachments if a.res_id})
            if not ids:
                for a in attachments:
                    a.is_orphan = True
                continue

            placeholders = ','.join(['%s'] * len(ids))
            sql = f"SELECT id FROM {table} WHERE id IN ({placeholders})"
            try:
                self.env.cr.execute(sql, tuple(ids))
                present = {r[0] for r in self.env.cr.fetchall()}
            except Exception as e:
                _logger.error("Error occurred while checking orphan attachments: %s", e)
                present = set()

            for a in attachments:
                a.is_orphan = (int(a.res_id) not in present)

    def unlink(self):
        """Override unlink to handle attachments in trash.
        Attachments in trash can be deleted by their owner or system group.
        """
        trash_days = self.env.context.get('trash_days', 30)
        for rec in self:
            if not rec.in_trash:
                self.filtered(lambda rec: not rec.in_trash).action_move_to_trash(days=trash_days)
        return super(IrAttachment, self.filtered(lambda rec: rec.in_trash)).unlink()

    def action_move_to_trash(self, days=30):
        """Mark attachments as moved to trash.

        Only writes fields; does not unlink.
        """
        now = fields.Datetime.now()
        expire = (fields.Datetime.to_datetime(now) + datetime.timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        for a in self:
            # permission: allow owner or system group
            if a.create_uid and a.create_uid.id != self.env.user.id and not self.env.user.has_group('base.group_system'):
                msg = 'You are not allowed to move this attachment to trash'
                raise AccessError(msg)
        self.write({
            'in_trash': True,
            'trash_date': now,
            'trash_uid': self.env.user.id,
            'expire_date': expire,
        })

    def action_restore(self):
        for a in self:
            if a.create_uid and a.create_uid.id != self.env.user.id and not self.env.user.has_group('base.group_system'):
                msg = 'You are not allowed to restore this attachment'
                raise AccessError(msg)
        self.write({
            'in_trash': False,
            'trash_date': False,
            'trash_uid': False,
            'expire_date': False,
        })

    @api.model
    def cron_empty_trash(self):
        now = fields.Datetime.now()
        attachments = self.search([('in_trash', '=', True), ('expire_date', '<=', now)])
        if attachments:
            attachments.unlink()
