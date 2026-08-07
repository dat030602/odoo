"""
Connector Sync Log
==================
Log model that records each sync run with status, record counts, and timing.
"""

from odoo import models, fields


class ConnectorSyncLog(models.Model):
    """Log entry for a sync run on a connector endpoint.

    Records the endpoint, start/end time, status, number of records
    fetched and imported, and any error messages.
    """

    _name = "connector.sync.log"
    _description = "Log for connector sync runs"
    _order = "create_date desc"

    endpoint_id = fields.Many2one(
        "connector.endpoint",
        string="Endpoint",
        required=True,
        ondelete="cascade",
        help="The endpoint that was synced.",
    )
    start_time = fields.Datetime(
        string="Start Time",
        help="When the sync started.",
    )
    end_time = fields.Datetime(
        string="End Time",
        help="When the sync finished.",
    )
    state = fields.Selection(
        [("running", "Running"), ("success", "Success"), ("error", "Error")],
        string="Status",
        help="The status of the sync run.",
    )
    records_fetched = fields.Integer(
        string="Records Fetched",
        help="Number of records fetched from the API.",
    )
    records_imported = fields.Integer(
        string="Records Imported",
        help="Number of records successfully imported.",
    )
    error_message = fields.Text(
        string="Error Message",
        help="Error message if the sync failed.",
    )
