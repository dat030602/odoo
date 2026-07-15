# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    def print_inventory_report(self):
        return self.env.ref('biz_inventory_report.inventory_report_pdf_action').report_action(self)