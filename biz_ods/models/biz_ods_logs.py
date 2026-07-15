# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class CallLogs(models.Model):
    _name = 'biz.ods.call.logs'
    _description = 'Call Logs'

    ods_call_log_type = fields.Selection(selection=[
        ('extension', 'Extension'),
        ('call_history', 'Call History'),
        ('outbound', 'Outbound')
    ], string="ODS Call Log Type")
    ods_message = fields.Text(string="Message")

    ods_sync_status = fields.Selection(selection=[
        ('sync_successful', 'Sync Successful'),
        ('sync_failed', 'Sync Failed')
    ], string="Sync Status")

    # outbound
    ods_status = fields.Selection(selection=[
        ('ringing', 'Ringing'),
        ('up', 'Up'),
        ('down', 'Down'),
        ('ringing_out', 'Ringing Out'),
        ('up_out', 'Up Out'),
        ('down_out', 'Down Out')
    ], string='Status')
    ods_direction = fields.Selection(selection=[
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound')
    ], string='Direction')

    # call_history
    number_of_call_history = fields.Integer(string="Number Of Call History")

    # extension
    number_of_extension = fields.Integer(string="Number Of Extension")



