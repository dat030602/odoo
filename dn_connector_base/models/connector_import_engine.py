"""
Connector Import Engine
=======================
Service that fetches data from REST API endpoints (with pagination support)
and imports raw data into dynamically created Odoo models.
"""

import json
import logging

from odoo import models, fields, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ConnectorImportEngine(models.AbstractModel):
    """Service for fetching and importing data from REST API endpoints.

    Handles pagination, schema discovery/application, raw data import with
    upsert logic, and missing field logging.
    """

    _name = "connector.import.engine"
    _description = "Service for importing raw data from REST APIs"

    def run_sync(self, endpoint):
        """Execute a full sync cycle for the given endpoint.

        Fetches all records from the API (with pagination), optionally
        discovers and applies schema, then imports each record.

        :param endpoint: The connector.endpoint record to sync.
        """
        connector = endpoint.connector_id
        cache = {"models": {}, "fields": {}}
        missing_log = {}

        all_records = self._fetch_paginated(endpoint)

        if connector.auto_create_schema and not endpoint._schema_applied:
            if all_records:
                discovered = endpoint.root_model_id.discover_schema(all_records[0])
                self.env["connector.schema.builder"].apply_schema(discovered)
            endpoint._schema_applied = True

        for raw in all_records:
            self._import_record(raw, endpoint.root_model_id, cache, missing_log)

        self._flush_missing_log(missing_log, endpoint)

    def _fetch_paginated(self, endpoint):
        """Fetch all records from the API endpoint with pagination support.

        Handles page number, offset/limit, and cursor-based pagination.

        :param endpoint: The connector.endpoint record to fetch from.
        :return: A list of raw record dicts.
        """
        connector = endpoint.connector_id
        results = []
        page = 1
        cursor = None
        while True:
            params = self._build_pagination_params(endpoint, page, cursor)
            resp = connector._request(
                endpoint.method, endpoint.path, params=params
            )
            batch = self._extract_target_path(resp, endpoint.target_json_path)
            if not batch:
                break
            results.extend(batch)
            if endpoint.pagination_type == "none":
                break
            if endpoint.pagination_type == "cursor":
                cursor = self._extract_target_path(
                    resp, endpoint.pagination_next_path
                )
                if not cursor:
                    break
            else:
                if len(batch) < endpoint.pagination_page_size:
                    break
                page += 1
        return results

    def _build_pagination_params(self, endpoint, page, cursor):
        """Build query parameters for pagination.

        :param endpoint: The connector.endpoint record.
        :param page: The current page number (for page-based pagination).
        :param cursor: The current cursor token (for cursor-based pagination).
        :return: A dict of query parameters.
        """
        params = {}
        if endpoint.pagination_type == "page":
            params[endpoint.pagination_param_page] = page
            params[endpoint.pagination_param_limit] = endpoint.pagination_page_size
        elif endpoint.pagination_type == "offset":
            params[endpoint.pagination_param_page] = (page - 1) * endpoint.pagination_page_size
            params[endpoint.pagination_param_limit] = endpoint.pagination_page_size
        elif endpoint.pagination_type == "cursor":
            if cursor:
                params[endpoint.pagination_param_page] = cursor
            params[endpoint.pagination_param_limit] = endpoint.pagination_page_size
        return params

    def _extract_target_path(self, data, path):
        """Extract a value from a nested dict using a dot-separated path.

        :param data: The data dict to extract from.
        :param path: Dot-separated path (e.g., 'result.data').
        :return: The value at the path, or None if not found.
        """
        if not path:
            return data
        node = data
        for key in path.split("."):
            node = node.get(key, {}) if isinstance(node, dict) else None
            if node is None:
                return None
        return node

    def _import_record(self, raw, signature, cache, missing_log, parent_id=None):
        """Import a single raw record into the corresponding Odoo model.

        Performs upsert based on x_external_id. Handles nested arrays by
        recursively importing child records.

        :param raw: The raw record dict from the API.
        :param signature: The connector.model.signature for this record.
        :param cache: Cache dict for models and fields (per sync run).
        :param missing_log: Accumulator for missing field logs.
        :param parent_id: The ID of the parent record (for nested records).
        :return: The created or updated Odoo record.
        """
        Model = self._get_cached_model(signature.target_model_name, cache)
        vals = {"x_payload": json.dumps(raw)}
        external_id = raw.get("id") or raw.get("Id") or raw.get("ID")
        if external_id is not None:
            vals["x_external_id"] = str(external_id)
        child_batches = {}

        for key, value in raw.items():
            field_name = f"x_{key}"
            field = self._get_cached_field(
                signature.target_model_name, field_name, cache
            )
            if field is None:
                missing_log.setdefault(
                    signature.target_model_name, set()
                ).add(field_name)
                continue
            if isinstance(value, list):
                child_batches[key] = value
            else:
                vals[field_name] = (
                    json.dumps(value) if isinstance(value, dict) else str(value)
                )

        record = None
        if vals.get("x_external_id"):
            record = Model.sudo().search(
                [("x_external_id", "=", vals["x_external_id"])], limit=1
            )
        if record:
            record.write(vals)
        else:
            record = Model.sudo().create(vals)

        for key, items in child_batches.items():
            child_signature = signature._get_child_signature(key)
            if not child_signature:
                continue
            for item in items:
                self._import_record(
                    item, child_signature, cache, missing_log, parent_id=record.id
                )

        return record

    def _get_cached_model(self, model_name, cache):
        """Get a model class from cache or load it from the registry.

        :param model_name: The Odoo model name (e.g., 'x_shopify_order').
        :param cache: The cache dict to store/retrieve the model class.
        :return: The Odoo model class.
        """
        if model_name not in cache["models"]:
            cache["models"][model_name] = self.env[model_name]
        return cache["models"][model_name]

    def _get_cached_field(self, model_name, field_name, cache):
        """Check if a field exists on a model, using cache for performance.

        :param model_name: The Odoo model name.
        :param field_name: The field name to check.
        :param cache: The cache dict for field lookups.
        :return: The field object if it exists, None otherwise.
        """
        cache_key = f"{model_name}.{field_name}"
        if cache_key not in cache["fields"]:
            Model = self._get_cached_model(model_name, cache)
            cache["fields"][cache_key] = field_name in Model._fields
        return cache["fields"][cache_key]

    def _flush_missing_log(self, missing_log, endpoint):
        """Write accumulated missing field logs to the database.

        Groups missing fields by model and creates one log entry per model.

        :param missing_log: Dict mapping model names to sets of missing field names.
        :param endpoint: The connector.endpoint record.
        """
        for model_name, field_names in missing_log.items():
            self.env["connector.missing.log"].sudo().create({
                "endpoint_id": endpoint.id,
                "model_name": model_name,
                "field_names": ", ".join(sorted(field_names)),
            })
