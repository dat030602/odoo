# -*- coding: utf-8 -*-
from odoo import fields, models
import logging
import json
import ast

_logger = logging.getLogger(__name__)

class PurchaseInvoicesList(models.Model):
    _name = 'purchase.invoices.list.ccv'
    _description = 'Bảng kê hóa đơn mua vào CCV'
    
    name = fields.Char('Tên bảng kê')
    date_from = fields.Date('Từ ngày', default=fields.Date.today(), required=True)
    date_to = fields.Date('Đến ngày', default=fields.Date.today(), required=True)
    state = fields.Selection([
        ('new', 'Mới'),
        ('locked', 'Đã khóa'),
    ], string='Trạng thái', default='new')
    line_ids = fields.One2many('purchase.invoices.list.line.ccv', 'parent_id', 'Chi tiết')
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    
    def name_get(self):
        result = []
        for record in self:
            date_from = record.date_from.strftime('%d/%m/%Y') if record.date_from else ''
            date_to = record.date_to.strftime('%d/%m/%Y') if record.date_to else ''
            name = '%s - %s - %s' % (record.name if record.name else '', date_from, date_to)
            result.append((record.id, name))
        return result
    
    def action_generate(self):
        """Tạo dòng từ account.move.line"""
        self.ensure_one()
        # self.line_ids.unlink()
        domain = [
            ('move_id.state', '=', 'posted'),
            ('move_id.report_date', '>=', self.date_from),
            ('move_id.report_date', '<=', self.date_to),
            ('move_id.move_type', 'in', ['in_invoice', 'in_refund', 'entry']),
        ]
        amls = self.env['account.move.line'].search(domain, order="date asc").filtered(lambda x: (x.account_id.is_vat_account and x.tax_line_id.type_tax_use == 'purchase') or (not x.account_id.is_vat_account and x.tax_ids.exists() and any([tax.type_tax_use == 'purchase' for tax in x.tax_ids])))
        move_ids = amls.mapped('move_id') - self.line_ids.mapped('move_id')
        self.line_ids._compute_account_move_line()

        # Create line records with aml_id
        line_vals = []
        
        # Process invoice moves (non-entry)
        for move in move_ids.filtered(lambda x: x.move_type != 'entry'):
            for invoice_line in move.invoice_line_ids.filtered(lambda x: x.balance != 0):
                line_vals.append({
                    'parent_id': self.id,
                    'aml_id': invoice_line.id,
                })
        
        # Process entry moves
        for move in move_ids.filtered(lambda x: x.move_type == 'entry'):
            entry_amls = move.line_ids.filtered(lambda line: line.account_id.is_vat_account and line.display_type != 'tax' and line.balance != 0)
            for aml in entry_amls:
                line_vals.append({
                    'parent_id': self.id,
                    'aml_id': aml.id,
                })
        
        if line_vals:
            self.env['purchase.invoices.list.line.ccv'].create(line_vals)
    
    
    def action_lock(self):
        self.write({
            'state': 'locked'
        })
    
    def action_unlock(self):
        self.write({
            'state': 'new'
        })
    
    def action_view_lines(self):
        action = self.env.ref('biz_purchase_invoices_list_ccv.action_purchase_invoices_list_line_ccv').sudo().read()[0]
        action['domain'] = [('parent_id', '=', self.id)]
        context = action.get('context', "{}")
        context = ast.literal_eval(context)
        context.update({
            'default_parent_id': self.id,
        })
        action['context'] = context
        return action
