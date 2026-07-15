# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class TypeClassification(models.Model):
    _name = 'type.classification'
    _description = 'Type Classification'
    _rec_name = 'name'

    name = fields.Char('Name')

class ConfigClassification(models.Model):
    _name = 'config.classification'
    _description = 'Config Classification'
    _rec_name = 'classification_id'

    classification_id = fields.Many2one('type.classification',string="Classification")
    proportion = fields.Float('Proportion')