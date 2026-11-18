# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MisaInvoiceTemplate(models.Model):
    _name = 'misa.invoice.template'
    _description = 'MISA e-Invoice Template'
    _order = 'inv_series asc, id desc'

    name = fields.Char(string='Template Name', compute='_compute_display_name', store=True)
    template_name = fields.Char(string='Template Title', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    template_id_misa = fields.Char(string='MISA IPTemplateID', index=True)
    inv_series = fields.Char(string='Invoice Series', required=True, index=True)
    inv_template_no = fields.Char(string='Template Form Number', default='1')
    inactive = fields.Boolean(string='Inactive (MISA)', default=False)
    active = fields.Boolean(string='Active', default=True)

    # Boolean flags from MISA API
    is_send_summary = fields.Boolean(string='Send Summary', help='Whether this template sends summary data to tax authority')
    is_petrol = fields.Boolean(string='Petrol Template', help='Petrol station invoice template')
    is_more_vat_rate = fields.Boolean(string='Multiple VAT Rates', help='Template supports multiple VAT rates')
    is_inherit_from_old = fields.Boolean(string='Old Template Format', help='True if inherited from old template format')

    # Parsed fields from InvSeries (e.g. 1C25MYY)
    invoice_type = fields.Selection([
        ('1', 'VAT Invoice (GTGT)'),
        ('2', 'Sales Invoice (Ban Hang)'),
        ('5', 'Electronic Ticket (Ve Dien Tu)'),
        ('6', 'Internal Stock Delivery Note (PXK)'),
        ('other', 'Other Invoice Type'),
    ], string='Invoice Type', compute='_compute_series_elements', store=True)

    tax_authority_code_type = fields.Selection([
        ('C', 'With Tax Authority Code (Co Ma CQT)'),
        ('K', 'Without Tax Authority Code (Khong Ma CQT)'),
        ('other', 'Other'),
    ], string='Tax Authority Code Status', compute='_compute_series_elements', store=True)

    invoice_system_type = fields.Selection([
        ('T', 'Standard Electronic Invoice (Hoa Don Thuong)'),
        ('M', 'Cash Register Generated (May Tinh Tien - POS)'),
        ('other', 'Other'),
    ], string='Invoice Form Type', compute='_compute_series_elements', store=True)

    @api.depends('template_name', 'inv_series', 'inv_template_no')
    def _compute_display_name(self):
        for rec in self:
            rec.name = f"[{rec.inv_series or ''}] {rec.template_name or ''}"

    @api.depends('inv_series')
    def _compute_series_elements(self):
        for rec in self:
            series = (rec.inv_series or '').strip().upper()
            # 1st char: invoice type
            if len(series) >= 1:
                first_char = series[0]
                if first_char in ['1', '2', '5', '6']:
                    rec.invoice_type = first_char
                else:
                    rec.invoice_type = 'other'
            else:
                rec.invoice_type = False

            # 2nd char: CQT code type
            if len(series) >= 2:
                second_char = series[1]
                if second_char in ['C', 'K']:
                    rec.tax_authority_code_type = second_char
                else:
                    rec.tax_authority_code_type = 'other'
            else:
                rec.tax_authority_code_type = False

            # 5th char: Form type (T = Standard, M = Cash register / MTT)
            if len(series) >= 5:
                fifth_char = series[4]
                if fifth_char in ['T', 'M']:
                    rec.invoice_system_type = fifth_char
                else:
                    rec.invoice_system_type = 'other'
            else:
                rec.invoice_system_type = False

    @api.model
    def sync_templates(self, company_id=None, year=None, invoice_with_code=None, ticket=None):
        """Synchronize invoice templates from MISA meInvoice (GET /invoice/templates)."""
        company = self.env['res.company'].browse(company_id) if company_id else self.env.company
        token = company.action_get_meinvoice_token()

        headers = {
            'ClientID': company.misa_client_id,
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        params = {}
        if year:
            params['year'] = str(year)
        if invoice_with_code is not None:
            params['invoiceWithCode'] = 'true' if invoice_with_code else 'false'
        if ticket is not None:
            params['ticket'] = 'true' if ticket else 'false'

        res = company._misa_request(
            service_type='meinvoice',
            endpoint='invoice/templates',
            method='GET',
            headers=headers,
            params=params,
        )

        if not res['is_success']:
            raise UserError(_("Failed to sync invoice templates from MISA: %s (%s)") % (res['error_message'], res['error_code']))

        data = res.get('data')
        template_list = []
        if isinstance(data, dict):
            template_list = data.get('Data') or []
        elif isinstance(data, list):
            template_list = data

        synced_count = 0
        for item in template_list:
            if not isinstance(item, dict):
                continue
            template_id_misa = item.get('IPTemplateID') or ''
            inv_series = item.get('InvSeries') or ''
            template_name = item.get('TemplateName') or inv_series

            vals = {
                'company_id': company.id,
                'template_id_misa': template_id_misa,
                'template_name': template_name,
                'inv_series': inv_series,
                'inv_template_no': str(item.get('InvTemplateNo') or '1'),
                'inactive': bool(item.get('Inactive')),
                'active': not bool(item.get('Inactive')),
                'is_send_summary': bool(item.get('IsSendSummary')),
                'is_petrol': bool(item.get('IsPetrol')),
                'is_more_vat_rate': bool(item.get('IsMoreVATRate')),
                'is_inherit_from_old': bool(item.get('IsInheritFromOldTemplate')),
            }

            existing = self.search([
                ('company_id', '=', company.id),
                ('inv_series', '=', inv_series)
            ], limit=1)
            if existing:
                existing.write(vals)
            else:
                self.create(vals)
            synced_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('MISA Templates Synchronized'),
                'message': _('Successfully synchronized %s template(s) for company %s.') % (synced_count, company.name),
                'type': 'success',
                'sticky': False,
            }
        }
