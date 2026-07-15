# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ExportDeliveryReportWizard(models.TransientModel):
    _name = 'export.delivery.report.wizard'
    _description = 'Export Delivery Orders Report Wizard'

    origin = fields.Char('Source Document')
    delivery_picking_ids = fields.Many2many(
        'stock.picking',
        string='Delivery Orders to Export',
        compute='_compute_delivery_picking_ids',
        store=False,
    )

    voter_id = fields.Many2one('res.users', string='Người Lập Phiếu')
    accounting_department_id = fields.Many2one('res.users', string='Phòng kế toán')
    factory_id = fields.Many2one('res.users', string='Nhà máy')
    trade_department_id = fields.Many2one('res.users', string='Phòng Thương mại')
    unit_heads_id = fields.Many2one('res.users', string='Thủ trưởng đơn vị')

    def default_get(self, fields_list):
        res = super(ExportDeliveryReportWizard, self).default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()
        chief_finance_id = env_params.get_param('ccv_bao_cao.chief_accountant_id', False)
        director_id = env_params.get_param('ccv_bao_cao.director_id', False)
        res['voter_id'] = self.env.user.id
        res['accounting_department_id'] = int(chief_finance_id) if chief_finance_id else False
        res['unit_heads_id'] = int(director_id) if director_id else False
        return res

    @api.depends('origin')
    def _compute_delivery_picking_ids(self):
        for wizard in self:
            po = self.env['purchase.order'].search([('name','=',wizard.origin)])
            wizard.delivery_picking_ids = po.stock_input_ids.mapped('picking_id')

    def action_export(self):
        return self.env.ref('purchase_to_delivery_report_ccv.action_import_report_xlsx').report_action(self)
