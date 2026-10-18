import fcntl
import hashlib
import json
import os
import re
import time

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pa = None

from odoo import api, fields, http, models, _
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request, Response

CACHE_DIR = os.environ.get('BI_PARQUET_CACHE_DIR', '/tmp/bi_parquet_cache')
USE_X_ACCEL = os.environ.get('BI_USE_X_ACCEL', '0') == '1'

FORBIDDEN_SQL_RE = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE|COPY|'
    r'pg_sleep|pg_read_file|res_users|ir_config_parameter)\b',
    re.IGNORECASE,
)
PARAM_RE = re.compile(r'(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)')


def validate_extract_sql(sql):
    if not sql or not sql.strip():
        raise ValueError(_("SQL cannot be empty."))
    if ';' in sql.strip().rstrip(';'):
        raise ValueError(_("Multiple SQL statements are forbidden."))
    if FORBIDDEN_SQL_RE.search(sql):
        raise ValueError(_("SQL contains forbidden keywords or system tables."))
    if ':company_ids' not in sql:
        raise ValueError(_("SQL must filter by :company_ids for multi-company isolation."))
    return sql.strip().rstrip(';')


def extract_sql_params(sql):
    return sorted({m for m in PARAM_RE.findall(sql or '') if m != 'company_ids'})


class BiDuckdbReport(models.Model):
    _name = 'bi.duckdb.report'
    _description = 'DuckDB Analytical Report'
    _check_company_auto = True

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    cache_ttl = fields.Integer(default=300, string='Cache TTL (s)')
    group_ids = fields.Many2many('res.groups', string='Allowed Groups')
    pg_extract_sql = fields.Text(
        string='PostgreSQL Extract SQL',
        required=True,
        default="SELECT id, name, create_date, company_id\nFROM sale_order\nWHERE company_id IN :company_ids\n  AND create_date >= :date_from",
    )
    view_ids = fields.One2many('bi.duckdb.report.view', 'report_id', string='Client DuckDB Views')

    @api.constrains('pg_extract_sql')
    def _check_pg_extract_sql(self):
        for rec in self:
            try:
                validate_extract_sql(rec.pg_extract_sql)
            except ValueError as err:
                raise ValidationError(str(err))

    def action_open_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'bi_duckdb_engine.report_action',
            'name': self.name,
            'context': {
                'active_id': self.id,
                'active_ids': [self.id],
                'active_model': 'bi.duckdb.report',
                'report_id': self.id,
                'default_report_id': self.id,
            },
            'params': {
                'report_id': self.id,
                'report_name': self.name,
                'param_names': extract_sql_params(self.pg_extract_sql),
                'views': [
                    {'id': v.id, 'name': v.name, 'duckdb_sql': v.duckdb_sql}
                    for v in self.view_ids
                ],
            },
        }


class BiDuckdbReportView(models.Model):
    _name = 'bi.duckdb.report.view'
    _description = 'DuckDB Client View Tab'
    _order = 'sequence, id'
    _check_company_auto = True

    report_id = fields.Many2one('bi.duckdb.report', required=True, ondelete='cascade', check_company=True)
    company_id = fields.Many2one('res.company', related='report_id.company_id', store=True, readonly=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, string='Tab Name')
    duckdb_sql = fields.Text(
        required=True,
        string='DuckDB SQL (queries raw_dataset)',
        default="SELECT company_id, COUNT(*) AS total_orders\nFROM raw_dataset\nGROUP BY ALL\nORDER BY total_orders DESC",
    )

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.report_id.name} - {rec.name}" if rec.report_id else rec.name


class BiDuckdbController(http.Controller):

    @http.route('/bi/duckdb/dataset/<int:report_id>', type='http', auth='user', methods=['POST'], csrf=False)
    def fetch_dataset(self, report_id):
        report = request.env['bi.duckdb.report'].browse(report_id)
        if not report.exists():
            return Response("Not found", status=404)
        if report.group_ids and not (report.group_ids & request.env.user.groups_id):
            raise AccessError(_("Access denied to this report."))

        payload = json.loads(request.httprequest.data or '{}')
        required_params = extract_sql_params(report.pg_extract_sql)
        bind_params = {k: payload.get(k) or None for k in required_params}
        bind_params['company_ids'] = tuple(request.env.companies.ids)

        os.makedirs(CACHE_DIR, exist_ok=True)
        ext = 'parquet' if pa else 'csv'
        raw_key = f"{report.id}:{report.write_date}:{json.dumps(bind_params, sort_keys=True)}"
        cache_key = hashlib.sha256(raw_key.encode()).hexdigest()
        file_path = os.path.join(CACHE_DIR, f"{cache_key}.{ext}")
        lock_path = os.path.join(CACHE_DIR, f"{cache_key}.lock")

        if not self._is_cache_fresh(file_path, report.cache_ttl):
            with open(lock_path, 'w') as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    if not self._is_cache_fresh(file_path, report.cache_ttl):
                        self._export_from_postgres(report.pg_extract_sql, bind_params, file_path, ext)
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)

        if USE_X_ACCEL:
            return Response("", headers=[
                ('Content-Type', 'application/octet-stream'),
                ('X-Dataset-Format', ext),
                ('X-Accel-Redirect', f'/_internal_bi_cache/{cache_key}.{ext}'),
            ])

        with open(file_path, 'rb') as f:
            data = f.read()
        return Response(data, headers=[
            ('Content-Type', 'application/octet-stream'),
            ('X-Dataset-Format', ext),
        ])

    def _is_cache_fresh(self, path, ttl):
        return os.path.exists(path) and (time.time() - os.path.getmtime(path) < ttl)

    def _export_from_postgres(self, raw_sql, bind_params, target_path, ext, env=None):
        clean_sql = validate_extract_sql(raw_sql)
        sql_with_placeholders = PARAM_RE.sub(r'%(\1)s', clean_sql)
        tmp_path = f"{target_path}.{os.getpid()}.tmp"
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        registry = env.registry if env else None
        if not registry:
            try:
                registry = request.env.registry
            except Exception:
                import odoo
                registry = odoo.registry(odoo.tools.config['db_name'] or 'odoo19')

        with registry.cursor() as ro_cr:
            ro_cr.execute("SET LOCAL TRANSACTION READ ONLY;")
            ro_cr.execute("SET LOCAL statement_timeout = '20000';")
            if ext == 'parquet':
                ro_cr.execute(sql_with_placeholders, bind_params)
                cols = [d[0] for d in ro_cr.description]
                rows = ro_cr.fetchall()
                arrays = [pa.array([r[i] for r in rows]) for i in range(len(cols))]
                pq.write_table(pa.Table.from_arrays(arrays, names=cols), tmp_path, compression='zstd')
            else:
                bound_sql = ro_cr.mogrify(sql_with_placeholders, bind_params).decode('utf-8')
                with open(tmp_path, 'wb') as out_f:
                    ro_cr._cnx.cursor().copy_expert(f"COPY ({bound_sql}) TO STDOUT WITH (FORMAT CSV, HEADER)", out_f)

        os.replace(tmp_path, target_path)
