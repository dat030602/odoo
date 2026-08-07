"""
Connector Endpoint
==================
Defines a specific API endpoint with method, path, pagination strategy,
and optional custom code for request preparation.
"""

from odoo import models, fields, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ConnectorEndpoint(models.Model):
    """Represents a single REST API endpoint within a connector configuration.

    Each endpoint defines the HTTP method, path, target JSON path for data
    extraction, pagination strategy, and optionally a custom code snippet
    for building request payloads from Odoo records.
    """

    _name = "connector.endpoint"
    _description = "A specific REST API endpoint configuration"
    _inherit = ["connector.code.mixin"]

    connector_id = fields.Many2one(
        "connector.config",
        string="Connector",
        required=True,
        ondelete="cascade",
        help="The connector configuration this endpoint belongs to.",
    )
    name = fields.Char(
        string="Name",
        required=True,
        help="A descriptive name for this endpoint (e.g., 'Orders', 'Products').",
    )
    method = fields.Selection(
        [
            ("GET", "GET"),
            ("POST", "POST"),
            ("PUT", "PUT"),
            ("PATCH", "PATCH"),
            ("DELETE", "DELETE"),
        ],
        string="HTTP Method",
        default="GET",
        required=True,
        help="The HTTP method to use for this endpoint.",
    )
    path = fields.Char(
        string="Path",
        required=True,
        help="The API path (e.g., /admin/api/2026-01/orders.json).",
    )
    target_json_path = fields.Char(
        string="Target JSON Path",
        help="Dot-separated path to the data array in the response (e.g., 'result.data' or 'orders').",
    )
    root_model_id = fields.Many2one(
        "connector.model.signature",
        string="Root Model Signature",
        help="The root model signature used for schema discovery and import.",
    )

    # Pagination
    pagination_type = fields.Selection(
        [
            ("none", "None"),
            ("page", "Page Number"),
            ("offset", "Offset/Limit"),
            ("cursor", "Cursor/Next Token"),
        ],
        string="Pagination Type",
        default="none",
        help="The pagination strategy used by this endpoint.",
    )
    pagination_param_page = fields.Char(
        string="Page Parameter",
        default="page",
        help="The query parameter name for page number pagination.",
    )
    pagination_param_limit = fields.Char(
        string="Limit Parameter",
        default="limit",
        help="The query parameter name for the page size.",
    )
    pagination_page_size = fields.Integer(
        string="Page Size",
        default=100,
        help="The number of records to fetch per page.",
    )
    pagination_next_path = fields.Char(
        string="Next Cursor Path",
        help="Dot-separated JSON path to the next cursor/token (e.g., 'meta.next_cursor').",
    )

    # Custom request preparation
    use_custom_prepare_request = fields.Boolean(
        string="Use Custom Request Preparation",
        help="If enabled, use the Python code field to build query params/body/headers "
        "instead of static configuration.",
    )
    _schema_applied = fields.Boolean(
        string="Schema Applied",
        default=False,
        help="Internal flag indicating whether schema has been applied for this endpoint.",
    )

    def button_execute_from_record(self):
        """Execute the endpoint from a business record (e.g., sale.order).

        Called from a button on a form view. Uses the active record(s) from
        the context to build the request payload, either via custom code or
        static preparation, then sends the request to the API.

        :return: The API response as a dict.
        :raises ValidationError: If no active model is found in context.
        """
        self.ensure_one()
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])
        if not active_model:
            raise ValidationError(_("No active model found in context."))
        records = (
            self.env[active_model].browse(active_ids)
            if active_model
            else self.env["base"].browse()
        )

        if self.use_custom_prepare_request:
            payload = self.execute_code(extra_context={"records": records})
        else:
            payload = self._prepare_request_static(records)

        return self.connector_id._request(
            method=self.method,
            path=self.path,
            json_body=payload,
        )

    def _prepare_request_static(self, records):
        """Build a static request payload from the given records.

        This is the default preparation method when custom code is not used.
        It serializes the records into a list of dicts.

        :param records: A recordset to serialize.
        :return: A list of dicts representing the records.
        """
        self.ensure_one()
        result = []
        for record in records:
            vals = {}
            for field_name, field in record._fields.items():
                if field.type in ("char", "text", "integer", "float", "boolean", "date", "datetime"):
                    vals[field_name] = record[field_name]
            result.append(vals)
        return result

    def button_sync(self):
        """Trigger a sync operation for this endpoint.

        Initiates the import engine to fetch data from the API and import
        it into the corresponding Odoo models.
        """
        self.ensure_one()
        return self.env["connector.import.engine"].run_sync(self)

    def _cron_sync_all_endpoints(self):
        """Cron job method to sync all active connector endpoints.

        Iterates through all active endpoints and triggers a sync for each.
        Logs the sync run in connector.sync.log.
        """
        endpoints = self.search([("connector_id.active", "=", True)])
        for endpoint in endpoints:
            sync_log = self.env["connector.sync.log"].sudo().create({
                "endpoint_id": endpoint.id,
                "state": "running",
                "start_time": fields.Datetime.now(),
            })
            try:
                self.env["connector.import.engine"].run_sync(endpoint)
                sync_log.write({
                    "state": "success",
                    "end_time": fields.Datetime.now(),
                })
            except Exception as e:
                _logger.exception(
                    "Sync failed for endpoint %s", endpoint.name
                )
                sync_log.write({
                    "state": "error",
                    "end_time": fields.Datetime.now(),
                    "error_message": str(e),
                })
