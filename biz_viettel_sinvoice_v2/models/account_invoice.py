# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api,_
import requests
import json
from odoo.exceptions import UserError,ValidationError
import uuid
import re

class AccountInvoice(models.Model):
    _inherit = "account.move"

    vat_sinvoice_number = fields.Char(string="VAT SInvoice Number", compute="_compute_vat_sinvoice_number")
    partner_vat_id = fields.Many2one('res.partner', 'Customer')
    sinvoice_ids = fields.One2many('viettel.sinvoice', 'invoice_id','Viettel Sinvoice')
    sinvoice_count = fields.Integer(compute="compute_sinvoice_count")
    number_invoice = fields.Char('Number Invoice', compute="_compute_number_invoice", store=True)
    adjust_invoice_ids = fields.Many2many('account.move', 'rel_move_adjust_inv', 'move_id','ivn_id', compute='compute_adjust_inv_count')
    count_adjust_invoice = fields.Integer(compute='compute_adjust_inv_count')

    sinvoice_adjust_id = fields.Many2one("viettel.sinvoice")
    sinvoice_line_adjust_id = fields.Many2one("viettel.sinvoice.line")
    origin_sinvoice_ids = fields.Many2many(
        'viettel.sinvoice',
        compute='_compute_origin_sinvoice_ids',
        string='Original S-Invoice',
        readonly=True,
    )
    origin_sinvoice_line_ids = fields.Many2many(
        'viettel.sinvoice.line',
        compute='_compute_origin_sinvoice_ids',
        string='Original issued S-Invoice lines',
        readonly=True,
    )
    origin_sinvoice_count = fields.Integer(compute='_compute_origin_sinvoice_ids')

    @api.depends(
        'move_type',
        'reversed_entry_id',
        'reversed_entry_id.sinvoice_ids',
        'reversed_entry_id.sinvoice_ids.einvoice_status',
        'reversed_entry_id.sinvoice_ids.sinvoice_line_ids',
        'reversed_entry_id.sinvoice_ids.sinvoice_line_ids.state',
    )
    def _compute_origin_sinvoice_ids(self):
        for res in self:
            origin_sinvoices = self.env['viettel.sinvoice']
            origin_sinvoice_lines = self.env['viettel.sinvoice.line']
            if res.move_type == 'out_refund' and res.reversed_entry_id:
                origin_sinvoices = res.reversed_entry_id.sinvoice_ids.filtered(
                    lambda sinvoice: sinvoice.einvoice_status == 'created'
                )
                origin_sinvoice_lines = origin_sinvoices.mapped('sinvoice_line_ids').filtered(
                    lambda line: line.state == 'created'
                )
            res.origin_sinvoice_ids = origin_sinvoices
            res.origin_sinvoice_line_ids = origin_sinvoice_lines
            res.origin_sinvoice_count = len(origin_sinvoice_lines)

    @api.depends('sinvoice_ids')
    def compute_adjust_inv_count(self):
        for res in self:
            res.adjust_invoice_ids = [(6,0, res.sinvoice_ids.mapped("adjust_invoice_ids").ids)]
            res.count_adjust_invoice = len(res.adjust_invoice_ids)

    def open_invoice_adjustment(self):
        return {
            'name': _("Invoice adjusted"),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id','in', self.adjust_invoice_ids.ids)]
        }


    @api.depends('sinvoice_ids')
    def compute_sinvoice_count(self):
        for res in self:
            res.sinvoice_count = len(res.sinvoice_ids)

    @api.depends(
        'sinvoice_ids',
        'sinvoice_ids.einvoice_status'
    )
    def _compute_vat_sinvoice_number(self):
        for record in self:
            if record.sinvoice_ids:
                for sin in record.sinvoice_ids:
                    name_list = []
                    for line in sin.sinvoice_line_ids:
                        if line.state == 'created':
                            name_list.append(line.invoiceNo)
                    record.vat_sinvoice_number = ', '.join([name for name in name_list])
            elif record.sinvoice_line_adjust_id:
                record.vat_sinvoice_number = record.sinvoice_line_adjust_id.invoiceNo
            else:
                record.vat_sinvoice_number = False
    
    def action_create_data_sinvoice(self):
        self.create_data_sinvoice()

    
    def create_data_sinvoice(self):
        partner_vat = self.partner_vat_id and self.partner_vat_id or self.partner_id
        val_sinvoice = {
            "invoice_id": self.id,
            "company_id": self.company_id.id,
            "name": self.name,
            "currency_id": self.currency_id.id,
            "partner_vat_id": self.partner_vat_id and self.partner_vat_id.id or self.partner_id.id,
            "date_invoice": self.invoice_date,
            "date": self.date,
            "company_currency_id": self.company_currency_id.id,
            "type": self.move_type,
            "journal_id": self.journal_id.id,
            "fiscal_position_id": self.fiscal_position_id and self.fiscal_position_id.id,
            'partner_vat': partner_vat.vat,
            'partner_vat_address': partner_vat.address_invoice_vat or self.get_partner_address(partner_vat),
            'partner_vat_name': partner_vat.name_vat
        }
        sinvoice_id = self.env['viettel.sinvoice'].create(val_sinvoice)
        if sinvoice_id:
            data_obj = self.env['viettel.sinvoice.data']
            seen_products = set()  # Theo dõi sản phẩm đã lấy (dùng cho entry)
            for line in self.invoice_line_ids:
                # Nếu là bút toán sổ cái (entry), chỉ lấy dòng đầu tiên cho mỗi sản phẩm
                # để tránh nhân đôi/nhân ba dòng hàng trên hóa đơn điện tử
                if self.move_type == 'entry':
                    if not line.product_id:
                        continue
                    if line.product_id.id in seen_products:
                        continue
                    seen_products.add(line.product_id.id)
                
                sale_line_id = line.sale_line_ids or False
                vals = sinvoice_id.create_data_sinvoice_line(line, sale_line_id=sale_line_id)
                for val in vals:
                    # Bắt buộc số lượng phải dương khi xuất hóa đơn từ bút toán kho
                    if self.move_type == 'entry' and val.get('quantity', 0) < 0:
                        val['quantity'] = abs(val['quantity'])
                    data_obj.create(val)
        return True 

    def get_partner_address(self, partner):
        address = ''
        if partner:
            if partner.street:
                address += partner.street
            if partner.wards_id:
                address += len(address) > 0 and ', ' + partner.wards_id.name or partner.wards_id.name
            if partner.district_id:
                address += len(address) > 0 and ', ' + partner.district_id.name or partner.district_id.name
            if partner.state_id:
                address += len(address) > 0 and ', ' + partner.state_id.name or partner.state_id.name
            if partner.country_id:
                address += len(address) > 0 and ', ' + partner.country_id.name or partner.country_id.name
        return address

    @api.depends('sinvoice_ids', 'sinvoice_ids.sinvoice_line_ids.invoiceNumber')
    def _compute_number_invoice(self):
        for res in self:
            if res.sinvoice_ids:
                latest_invoice = res.sinvoice_ids.sorted(key=lambda r: r.create_date, reverse=True)[:1]
                if latest_invoice and latest_invoice.sinvoice_line_ids and latest_invoice.name: 
                    invoice_lines = latest_invoice.sinvoice_line_ids.filtered(lambda line: line.state == 'created')
                    sorted_lines = invoice_lines.sorted(key=lambda line: line.create_date, reverse=True)
                    invoice_line = sorted_lines[:1] 
                    invoice_no = invoice_line.invoiceNo
                    if invoice_no:
                        # Extract digits from the end and pad to 7 characters
                        match = re.search(r'(\d+)$', invoice_no)
                        if match:
                            res.number_invoice = match.group(1).zfill(7)
                        else:
                            res.number_invoice = invoice_no
    
class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    sale_line_ids = fields.Many2many(
        'sale.order.line',
        'sale_order_line_invoice_rel',
        'invoice_line_id', 'order_line_id',
        string='Sales Order Lines', readonly=False, copy=False)
    
