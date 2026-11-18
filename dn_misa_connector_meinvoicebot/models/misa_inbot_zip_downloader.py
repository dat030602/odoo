# -*- coding: utf-8 -*-
import base64
import io
import json
import logging
import zipfile
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MisaInbotZipDownloader(models.Model):
    _name = 'misa.inbot.zip.downloader'
    _description = 'MISA INBOT Asynchronous ZIP Downloader'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Task Name', default=lambda self: _('ZIP Download Task'))
    download_key = fields.Char(string='Download Key', copy=False, index=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    subscriber_id = fields.Char(string='Subscriber ID')
    org_id = fields.Char(string='Organization ID')
    file_type = fields.Selection([
        ('1', '1 - XML + PDF'),
        ('2', '2 - PDF Only'),
        ('3', '3 - XML Only'),
    ], string='File Type', default='1', required=True)

    is_inbot = fields.Boolean(string='Is Inbound', default=True)
    invoice_ids = fields.Text(
        string='Invoice IDs (JSON array)',
        help='JSON list of INBOT invoice IDs included in this download request'
    )
    invoice_count = fields.Integer(string='Invoice Count', default=0)
    scheduled_time = fields.Datetime(string='Scheduled Execution Time', index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('downloading', 'Downloading'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', tracking=True, index=True)
    error_message = fields.Text(string='Error Message')

    def action_request_zip_key(self):
        """Call POST /meinvoicebot/v1/{SubscribersId}/{organizationId}/download/zip to get download key."""
        self.ensure_one()
        subscriber_id = self.subscriber_id or self.company_id.misa_inbot_subscribers_id
        org_id = self.org_id
        if not subscriber_id or not org_id:
            org = self.env['misa.organization'].search([('company_id', '=', self.company_id.id)], limit=1)
            if org:
                subscriber_id = subscriber_id or org.subscriber_id
                org_id = org_id or org.org_id

        if not subscriber_id or not org_id:
            raise UserError(_("Missing SubscribersId or OrganizationId for company %s.") % self.company_id.name)

        inv_ids = []
        if self.invoice_ids:
            try:
                inv_ids = json.loads(self.invoice_ids)
            except Exception:
                inv_ids = [x.strip() for x in self.invoice_ids.split(',') if x.strip()]

        if not inv_ids:
            raise UserError(_("No invoice IDs provided for ZIP download."))

        endpoint = f"meinvoicebot/v1/{subscriber_id}/{org_id}/download/zip"
        body = {
            'FileType': int(self.file_type),
            'LstInvID': inv_ids,
            'IsInbot': self.is_inbot,
        }

        res = self.company_id._execute_inbot_api(endpoint, method='POST', json_data=body)
        if not res.get('is_success'):
            self.write({
                'state': 'failed',
                'error_message': f"Request Key Failed: {res.get('error_message')} ({res.get('error_code')})",
            })
            raise UserError(_("Failed to request ZIP download key: %s") % res.get('error_message'))

        res_data = res.get('data')
        key = None
        if isinstance(res_data, dict):
            key = res_data.get('Key') or res_data.get('Data') or res_data.get('key')
        elif isinstance(res_data, str):
            key = res_data

        if not key:
            raise UserError(_("No Download Key returned in response: %s") % res_data)

        # MISA rule: wait at least 10 seconds per invoice
        delay_sec = max(15, len(inv_ids) * 10)
        sched_time = fields.Datetime.now() + timedelta(seconds=delay_sec)

        self.write({
            'download_key': key,
            'subscriber_id': subscriber_id,
            'org_id': org_id,
            'invoice_count': len(inv_ids),
            'scheduled_time': sched_time,
            'state': 'scheduled',
            'error_message': False,
        })
        return True

    def action_download_and_extract_zip(self):
        """Call GET .../download/{Key}/download, parse base64 ZIP and extract XML/PDF to documents."""
        self.ensure_one()
        if not self.download_key:
            raise UserError(_("Cannot download without a Download Key."))

        subscriber_id = self.subscriber_id or self.company_id.misa_inbot_subscribers_id
        org_id = self.org_id
        endpoint = f"meinvoicebot/v1/{subscriber_id}/{org_id}/download/{self.download_key}/download"

        self.state = 'downloading'
        res = self.company_id._execute_inbot_api(endpoint, method='GET')
        if not res.get('is_success'):
            self.write({
                'state': 'failed',
                'error_message': f"Download failed: {res.get('error_message')} ({res.get('error_code')})",
            })
            return False

        zip_base64 = None
        res_data = res.get('data')
        if isinstance(res_data, dict):
            zip_base64 = res_data.get('Data') or res_data.get('FileContent')
        elif isinstance(res_data, str):
            zip_base64 = res_data

        if not zip_base64:
            self.write({
                'state': 'failed',
                'error_message': _("Empty ZIP content received from server."),
            })
            return False

        try:
            zip_bytes = base64.b64decode(zip_base64)
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                for file_info in z.infolist():
                    if file_info.is_dir():
                        continue
                    filename = file_info.filename
                    content = z.read(filename)
                    encoded_content = base64.b64encode(content)

                    # Extract Invoice ID or No from filename or matching documents
                    # Format typically: "{InvoiceNo}_{InvoiceId}.xml" or "{InvoiceId}.xml"
                    self._match_and_attach_file(filename, encoded_content)

            self.write({
                'state': 'done',
                'error_message': False,
            })
            return True
        except Exception as e:
            _logger.exception("Error extracting ZIP for task %s: %s", self.id, e)
            self.write({
                'state': 'failed',
                'error_message': str(e),
            })
            return False

    def _match_and_attach_file(self, filename, encoded_content):
        """Match file to misa.inbot.document and attach, respecting no-overwrite for user-uploaded XML."""
        doc_obj = self.env['misa.inbot.document']
        fname_lower = filename.lower()

        # Find document candidate by invoice_id or invoice_no in filename
        inv_ids = []
        if self.invoice_ids:
            try:
                inv_ids = json.loads(self.invoice_ids)
            except Exception:
                inv_ids = []

        matched_doc = False
        for i_id in inv_ids:
            if i_id.lower() in fname_lower:
                matched_doc = doc_obj.search([('invoice_id', '=', i_id), ('company_id', '=', self.company_id.id)], limit=1)
                if matched_doc:
                    break

        if not matched_doc:
            # Try searching by exact or partial invoice_no
            base_name = filename.split('.')[0]
            matched_doc = doc_obj.search([
                ('company_id', '=', self.company_id.id),
                '|',
                ('invoice_no', '=', base_name),
                ('trans_id', '=', base_name)
            ], limit=1)

        if matched_doc:
            vals = {}
            if fname_lower.endswith('.xml'):
                # Rule: If source_type == '1' (User uploaded XML), DO NOT overwrite user XML!
                if matched_doc.source_type != '1':
                    vals['xml_file'] = encoded_content
                    vals['xml_filename'] = filename
            elif fname_lower.endswith('.pdf'):
                vals['pdf_file'] = encoded_content
                vals['pdf_filename'] = filename

            if vals:
                matched_doc.write(vals)

    @api.model
    def process_scheduled_zip_downloads(self):
        """Cron job to process scheduled ZIP downloads that reached their scheduled time."""
        now = fields.Datetime.now()
        tasks = self.search([
            ('state', '=', 'scheduled'),
            ('scheduled_time', '<=', now)
        ], limit=10)
        for task in tasks:
            try:
                task.action_download_and_extract_zip()
            except Exception as e:
                _logger.error("Error executing scheduled ZIP download task %s: %s", task.id, e)
