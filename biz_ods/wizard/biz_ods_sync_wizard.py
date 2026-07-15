# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class OdsSyncWizard(models.TransientModel):
    _name = 'biz.ods.sync.wizard'
    _description = 'Sync'

    ods_status = fields.Selection(selection=[
        ('get_extension', 'Get Extension'),
        ('get_call_history', 'Get Call History')
    ], string="Status")
    ods_type_get = fields.Selection(selection=[
        ('0', 'All'),
        ('1', 'Inbound'),
        ('2', 'Outbound'),
        ('3', 'Internal'),
        ('4', 'Missed'),
        ('5', 'Answer Group'),
        ('6', 'Missed Group'),
        ('7', 'All Missed')
    ], string="Type Get", default="0")
    ods_from_date = fields.Datetime(string="From Date")
    ods_to_date = fields.Datetime(string="To Date")

    def apply(self):
        if self.ods_status == 'get_call_history':
            try:
                self.env['biz.ods.call.history'].with_context(
                    ods_type_get=self.ods_type_get,
                    ods_from_datetime=self.ods_from_date,
                    ods_to_datetime=self.ods_to_date).action_get_call_history()
                self._cr.commit()
                self._cr.reset()
                # self.env['biz.ods.call.history'].action_run_cron_audio_call_history()
            except Exception as error:
                _logger.info(error)
        elif self.ods_status == 'get_extension':
            self.env['biz.ods.extension'].action_get_extension()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
