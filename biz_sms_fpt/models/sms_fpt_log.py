# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import requests
import json
import logging
_logger = logging.getLogger(__name__)
import socket
import pprint
import pprint


class SmsFptLog(models.Model):
    _name = 'sms.fpt.log'
    _order = "create_date desc"
    _description = 'Sms fpt log'

    name = fields.Char('Name')
    url = fields.Char('Url')
    create_on = fields.Datetime('Create on')
    data = fields.Text('Data', default={})
    data_response = fields.Text('Data Response', default={})
    state = fields.Selection([
            ('success','Success'),
            ('fail','Fail'),
        ], default='fail')
    error = fields.Char('Error')
