import json
import logging
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Rate limit tracking: max 10 requests per 60s for auth/sampling APIs
_RATE_LIMIT_BUCKET = {}


class MisaQueueJob(models.Model):
    _name = 'misa.queue.job'
    _description = 'MISA Sequential Queue Job'
    _order = 'create_date asc, id asc'

    name = fields.Char(string='Job Reference', required=True, default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    inv_series = fields.Char(string='Invoice Series', index=True, help='Invoice Series used for row-level concurrency locking')

    service_type = fields.Selection([
        ('meinvoice', 'meInvoice (Publishing)'),
        ('inbot', 'INBOT (Input/Output)')
    ], string='Service', required=True, default='meinvoice', index=True)

    action_type = fields.Selection([
        ('publish_invoice', 'Publish Invoice'),
        ('create_draft', 'Create Draft Invoice'),
        ('sync_inbot_invoices', 'Sync INBOT Invoices'),
        ('update_accounting', 'Update Accounting State'),
        ('update_payment', 'Update Payment State'),
        ('download_zip', 'Download Zip Files'),
        ('custom', 'Custom Action')
    ], string='Action Type', required=True, default='publish_invoice')

    model_name = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related Record ID')
    payload = fields.Text(string='Payload Data (JSON)')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
        ('retry', 'Waiting Retry')
    ], string='Status', default='queued', required=True, index=True)

    retry_count = fields.Integer(string='Retry Count', default=0)
    max_retries = fields.Integer(string='Max Retries', default=3)
    next_retry_time = fields.Datetime(string='Next Retry Time')
    error_message = fields.Text(string='Last Error Message')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('misa.queue.job') or _('Job %s') % fields.Datetime.now()
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # Rate Limit & Batch Limit Enforcement
    # -------------------------------------------------------------------------
    @api.model
    def check_rate_limit(self, key='auth_or_sample', max_requests=10, window_seconds=60):
        """Rate limit helper enforcing 10 req/60s on auth/sampling APIs."""
        now = fields.Datetime.now()
        history = _RATE_LIMIT_BUCKET.get(key, [])
        cutoff = now - timedelta(seconds=window_seconds)

        # Retain only timestamps within window
        history = [ts for ts in history if ts > cutoff]
        if len(history) >= max_requests:
            return False, (history[0] + timedelta(seconds=window_seconds) - now).total_seconds()

        history.append(now)
        _RATE_LIMIT_BUCKET[key] = history
        return True, 0

    @api.model
    def validate_batch_limits(self, invoice_records, lines_per_invoice=400):
        """Enforce batch limits: max 30 invoices per request, max 400 lines per invoice."""
        if len(invoice_records) > 30:
            raise UserError(_("Batch limit exceeded: Maximum 30 invoice documents per request (got %s).") % len(invoice_records))

        for inv in invoice_records:
            line_count = len(inv.line_ids) if hasattr(inv, 'line_ids') else 0
            if line_count > lines_per_invoice:
                raise UserError(_("Invoice %s exceeds maximum allowed line items (%s / %s).") % (inv.name, line_count, lines_per_invoice))
        return True

    # -------------------------------------------------------------------------
    # Queue Processing Execution
    # -------------------------------------------------------------------------
    @api.model
    def process_queue_jobs(self, limit=20):
        """Sequential Queue Job Processor invoked by Cron."""
        now = fields.Datetime.now()

        # Find series of ready jobs
        ready_domain = [
            ('state', 'in', ['queued', 'retry']),
            '|', ('next_retry_time', '=', False), ('next_retry_time', '<=', now)
        ]
        job_candidates = self.search(ready_domain, order='create_date asc', limit=limit)
        if not job_candidates:
            return

        # Group by series or None
        series_set = set(job_candidates.mapped('inv_series'))

        for series in series_set:
            self._process_series_jobs(series)

    @api.model
    def _process_series_jobs(self, series):
        """Process jobs sequentially for a specific invoice series with row lock."""
        now = fields.Datetime.now()
        domain = [
            ('state', 'in', ['queued', 'retry']),
            ('inv_series', '=', series),
            '|', ('next_retry_time', '=', False), ('next_retry_time', '<=', now)
        ]

        # Use with_for_update to lock rows and prevent concurrent workers on same series
        jobs = self.search(domain, order='create_date asc', limit=10)
        if not jobs:
            return

        try:
            # Query row lock
            jobs_locked = jobs.with_for_update(nowait=True)
        except Exception:
            _logger.info("Series %s currently locked by another worker, skipping.", series)
            return

        for job in jobs_locked:
            job._execute_job()

    def _execute_job(self):
        """Execute single queue job with auto-retry logic."""
        self.ensure_one()
        self.write({'state': 'processing'})

        try:
            # Check rate limiting if relevant
            if self.action_type in ['create_draft', 'custom']:
                allowed, wait_sec = self.check_rate_limit(f"job_{self.company_id.id}")
                if not allowed:
                    # Delay job
                    self.write({
                        'state': 'retry',
                        'next_retry_time': fields.Datetime.now() + timedelta(seconds=max(5, int(wait_sec))),
                        'error_message': _("Rate limit (10 req/60s) reached. Rescheduling...")
                    })
                    return

            # Dispatch action according to action_type or target model
            if self.model_name and self.res_id:
                record = self.env[self.model_name].browse(self.res_id)
                if hasattr(record, 'action_execute_queue_job'):
                    record.action_execute_queue_job(self)
                elif hasattr(record, 'action_misa_publish_now'):
                    record.action_misa_publish_now()

            self.write({
                'state': 'done',
                'error_message': False,
            })

        except Exception as e:
            err_text = str(e)
            _logger.error("Error executing MISA Queue Job %s: %s", self.name, err_text, exc_info=True)

            # Auto retry on specific MISA errors: 429 TooManyRequests, InvoiceDuplicated, InvoiceNumberNotCotinuous
            auto_retry_errors = ['429', 'TooManyRequests', 'InvoiceDuplicated', 'InvoiceNumberNotCotinuous']
            is_auto_retry = any(err in err_text for err in auto_retry_errors)

            if is_auto_retry or (self.retry_count < self.max_retries):
                new_retry = self.retry_count + 1
                delay_sec = 60 * new_retry  # Exponential-ish backoff
                self.write({
                    'state': 'retry',
                    'retry_count': new_retry,
                    'next_retry_time': fields.Datetime.now() + timedelta(seconds=delay_sec),
                    'error_message': err_text,
                })
            else:
                self.write({
                    'state': 'failed',
                    'error_message': err_text,
                })

    def action_retry(self):
        """Manual trigger to retry a failed or waiting job."""
        for rec in self:
            rec.write({
                'state': 'queued',
                'next_retry_time': False,
            })
            rec._execute_job()
