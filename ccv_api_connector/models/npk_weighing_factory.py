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


class NpkWeighingFactory(models.Model):
    _name = 'npk.weighing.factory'
    _description = 'NPK Weighing Factory'
    _order = 'name'

    name = fields.Char(string="Tên nhà máy")
    code = fields.Char(string="Mã nhà máy")
    address = fields.Char(string="Địa chỉ")
    active = fields.Boolean(string="Hoạt động", default=True)
    picking_type_id = fields.Many2one('stock.picking.type', string="Kho", domain=[("code", "=", "mrp_operation")])

    def _cron_update_factory(self):
        """Cron job to update factory"""
        factories = self.search(['|', ('active', '=', True), ('active', '=', False)])
        responses = self.env['npk.weighing.history']._fetch_factories()
        for response in responses:
            factory = factories.filtered(lambda x: x.code == response.get('Id', False))
            if factory:
                factory.write({
                    'active': response.get('IsDisabled', False) == 0
                })
            else:
                self.create({
                    'name': response.get('Ten', False),
                    'code': response.get('Id', False),
                    'address': response.get('DiaChi', False),
                    'active': response.get('IsDisabled', False) == 0
                })

