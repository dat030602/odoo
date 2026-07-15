from odoo import models, fields, _
from odoo.exceptions import ValidationError


class AccountMoveUpdateInvoiceInfoWizard(models.TransientModel):
    _name = 'wz.account.move.update.invoice.info'
    _description = 'Wizard cập nhật ref/series/date invoice'

    ref = fields.Char(string='Mã hóa đơn')
    series = fields.Char(string='Kí hiệu hóa đơn')
    date_invoice = fields.Date(string='Ngày hóa đơn')

    def action_apply(self):
        self.ensure_one()
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids', [])

        if active_model != 'account.move' or not active_ids:
            raise ValidationError(_('Không tìm thấy hóa đơn cần cập nhật.'))

        moves = self.env['account.move'].browse(active_ids).exists()
        if not moves:
            raise ValidationError(_('Không tìm thấy hóa đơn cần cập nhật.'))

        move_vals = {}
        if 'ref' in moves._fields:
            move_vals['ref'] = self.ref
        if 'series' in moves._fields:
            move_vals['series'] = self.series
        if 'date_invoice' in moves._fields:
            move_vals['date_invoice'] = self.date_invoice
        if 'invoice_date' in moves._fields:
            move_vals['invoice_date'] = self.date_invoice

        if move_vals:
            moves.write(move_vals)

        line_vals = {}
        lines = moves.line_ids
        if 'invoice_number' in lines._fields:
            line_vals['invoice_number'] = self.ref
        if 'invoice_code' in lines._fields:
            line_vals['invoice_code'] = self.series
        if 'date_invoice' in lines._fields:
            line_vals['date_invoice'] = self.date_invoice

        if line_vals and lines:
            lines.write(line_vals)

        return