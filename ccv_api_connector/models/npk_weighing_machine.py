from odoo import models, fields, api
import logging
import uuid
import requests
from odoo.exceptions import UserError
import datetime
import json
import ast

_logger = logging.getLogger(__name__)

def _parse_api_datetime(dt_str):
    if not dt_str or not isinstance(dt_str, str):
        return False
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1]
        try:
            dt_obj = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            dt_obj = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
        return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return False

class NpkWeighingMachine(models.Model):
    _name = 'npk.weighing.machine'
    _description = 'NPK Weighing Machine'
    _order = 'name'

    name = fields.Char(string="Tên máy cân")
    factory_id = fields.Many2one('npk.weighing.factory', string="Nhà máy")
    code = fields.Char(string="Mã máy cân")
    tag_ids = fields.Many2many('mrp.bom.tags', string="Thẻ sản phẩm")
    active = fields.Boolean(string="Hoạt động", default=True)
    is_default = fields.Boolean(string="Mặc định", default=False)
    
    def _cron_update_machine(self):
        """Cron job to update machine"""
        machines = self.search(['|', ('active', '=', True), ('active', '=', False)])
        factories = self.env['npk.weighing.factory'].search([('active', '=', True)])
        for factory in factories:
            responses = self.env['npk.weighing.history']._fetch_machines_by_factory(factory.code)
            for response in responses:
                machine = machines.filtered(lambda x: int(x.code) == response.get('Id', False))
                if machine:
                    machine.write({
                        'active': response.get('IsDisabled', False) == 0
                    })
                else:
                    self.create({
                        'name': response.get('Ten', False),
                        'factory_id': factory.id,
                        'code': response.get('Id', False),
                        'active': response.get('IsDisabled', False) == 0
                    })

    def action_get_current_ticket(self):
        """Get current ticket"""
        history_env = self.env['npk.weighing.history']
        tickets = history_env._fetch_running_tickets_by_machine(self.code)
        return history_env.action_open_weighing_ticket(tickets)
