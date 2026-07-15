# -*- coding: utf-8 -*-
from odoo import fields, models
import logging
import ast

_logger = logging.getLogger(__name__)

class SaleInvoicesList(models.Model):
    _name = 'sale.invoices.list.ccv'
    _description = 'Bảng kê hóa đơn bán ra CCV'
    
    name = fields.Char('Tên bảng kê')
    from_date = fields.Date('Từ ngày', default=fields.Date.today(), required=True)
    to_date = fields.Date('Đến ngày', default=fields.Date.today(), required=True)
    state = fields.Selection([
        ('new', 'Mới'),
        ('locked', 'Đã khóa'),
    ], string='Trạng thái', default='new')
    line_ids = fields.One2many('sale.invoices.list.line.ccv', 'parent_id', 'Chi tiết')
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    
    def name_get(self):
        result = []
        for record in self:
            from_date = record.from_date.strftime('%d/%m/%Y') if record.from_date else ''
            to_date = record.to_date.strftime('%d/%m/%Y') if record.to_date else ''
            name = '%s - %s - %s' % (record.name if record.name else '', from_date, to_date)
            result.append((record.id, name))
        return result
    
    def action_generate(self):
        """Tạo dòng từ account.move.line cho hóa đơn bán ra"""
        self.ensure_one()
        
        sinvoice_ids = self.env['viettel.sinvoice'].search([
            ('state', '=', 'created'),
            ('invoiceIssuedDate', '>=', self.from_date),
            ('invoiceIssuedDate', '<=', self.to_date),
            ('company_id', '=', self.company_id.id),
        ])
        move_ids = sinvoice_ids - self.line_ids.mapped('move_id')
        self.line_ids._compute_account_move_line()
        
        # Create line records with aml_id
        line_vals = []
        
        # Process invoice moves (non-entry)
        for line in move_ids.sinvoice_data_ids.filtered(lambda r: r.display_type is False):
            line_vals.append({
                'parent_id': self.id,
                'aml_id': line.id,
            })
        
        if line_vals:
            self.env['sale.invoices.list.line.ccv'].create(line_vals)
    
    def action_lock(self):
        self.write({
            'state': 'locked'
        })
    
    def action_unlock(self):
        self.write({
            'state': 'new'
        })
    
    def action_view_lines(self):
        action = self.env.ref('biz_sales_invoice_list_ccv.action_sale_invoices_list_line_ccv').sudo().read()[0]
        action['domain'] = [('parent_id', '=', self.id)]
        context = action.get('context', "{}")
        context = ast.literal_eval(context)
        context.update({
            'default_parent_id': self.id,
        })
        action['context'] = context
        return action
