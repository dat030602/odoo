from platform import machine
from odoo import models, fields, api
import logging
import requests
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
import json

_logger = logging.getLogger(__name__)

class CcvMrpPlanExport(models.Model):
    _inherit = "ccv.mrp.plan.export"

    def action_create_mrp_order(self):
        res = super(CcvMrpPlanExport, self).action_create_mrp_order()
        
        # res._onchange_product_id_tag_ids()
        # try:
        #     history_env = self.env['npk.weighing.history']
        #     w_ids = history_env
        #     now = fields.Datetime.now() + timedelta(hours=7)
        #     for mrp in res:
        #         if mrp.machine_id:
        #             machine = mrp.machine_id
        #         else:
        #             machine = self.env['npk.weighing.machine'].search([('factory_id.picking_type_id', '=', mrp.picking_type_id.id)])
        #             machine_default = machine.filtered(lambda m: m.is_default)
        #             if machine_default:
        #                 machine = machine_default[0]
        #             else:
        #                 machine = machine[0] if machine else False
        #         w_ids |= history_env.create({
        #             'production_id': mrp.id,
        #             'machine_id': machine.id,
        #             'plan_counter': mrp.bag_number,
        #         })
        #     w_ids._compute_production_id()
        #     w_ids._create_weighing_list_ticket()
        #     for mrp in res.filtered(lambda m: m.machine_id):
        #         mrp.message_post(body="Đã đẩy lên cân thành công vào lúc %s !!!" % now.strftime('%Y-%m-%d %H:%M:%S'))
        # except Exception as e:
        #     _logger.error("Error occurred while creating weighing history: %s", str(e))

        return res
