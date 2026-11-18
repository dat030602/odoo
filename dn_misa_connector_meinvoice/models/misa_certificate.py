# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MisaCertificate(models.Model):
    _name = 'misa.certificate'
    _description = 'MISA Digital Certificate'
    _order = 'valid_to desc, id desc'

    name = fields.Char(string='Subject Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    serial_number = fields.Char(string='Serial Number', required=True, index=True)
    issuer = fields.Char(string='Issuer')
    valid_from = fields.Datetime(string='Valid From')
    valid_to = fields.Datetime(string='Valid To')
    sign_type = fields.Selection([
        ('1', 'USB Token / Soft Certificate'),
        ('2', 'HSM / Remote eSign'),
        ('5', 'POS / Cash Register'),
    ], string='Sign Type', default='2')
    is_active_cert = fields.Boolean(string='Valid Status', compute='_compute_is_active_cert', store=True)

    @api.depends('valid_from', 'valid_to')
    def _compute_is_active_cert(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_active_cert = bool(
                (not rec.valid_from or rec.valid_from <= now) and
                (not rec.valid_to or rec.valid_to >= now)
            )

    @api.model
    def sync_certificates(self, company_id=None):
        """Synchronize remote digital certificates (GET /invoice/get-certificates)."""
        company = self.env['res.company'].browse(company_id) if company_id else self.env.company
        token = company.action_get_meinvoice_token()

        headers = {
            'ClientID': company.misa_client_id,
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        res = company._misa_request(
            service_type='meinvoice',
            endpoint='invoice/get-certificates',
            method='GET',
            headers=headers,
        )

        if not res['is_success']:
            raise UserError(_("Failed to fetch digital certificates from MISA: %s (%s)") % (res['error_message'], res['error_code']))

        data = res.get('data')
        cert_list = []
        if isinstance(data, dict):
            cert_list = data.get('Data') or []
        elif isinstance(data, list):
            cert_list = data

        synced_count = 0
        for item in cert_list:
            if not isinstance(item, dict):
                continue
            serial = item.get('SerialNumber') or item.get('serialNumber') or ''
            subject_name = item.get('SubjectName') or item.get('subjectName') or serial
            issuer = item.get('Issuer') or item.get('issuer') or ''
            valid_from = item.get('ValidFrom') or item.get('validFrom')
            valid_to = item.get('ValidTo') or item.get('validTo')

            vals = {
                'company_id': company.id,
                'name': subject_name,
                'serial_number': serial,
                'issuer': issuer,
                'valid_from': valid_from,
                'valid_to': valid_to,
                'sign_type': '2',
            }

            existing = self.search([
                ('company_id', '=', company.id),
                ('serial_number', '=', serial)
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
                'title': _('Digital Certificates Synchronized'),
                'message': _('Successfully synchronized %s certificate(s) for company %s.') % (synced_count, company.name),
                'type': 'success',
                'sticky': False,
            }
        }
