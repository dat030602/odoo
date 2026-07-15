from odoo import models, api
from ...models.component import vietnam_number, format_float_number, vietnam_number_upper,format_float_number_weight
import logging

_logger = logging.getLogger(__name__)

class RpPlantYieldChargeDailyWork(models.AbstractModel):
    _name = 'report.ccv_custom_field.rp_plant_yield_charge_daily_work'
    _description = 'Báo cáo Sản lượng Chất cây - Xạc cây - Công nhật'
    
    def _get_product_line_ids(self, docs):
        result = {}
        for doc in docs:
            arr = []
            quantity_by_uom = {}
            d_quantity_by_uom = {}
            
            product_uom_ids = doc.product_line_ids.mapped('product_uom_id')

            for product_uom_id in product_uom_ids:
                quantity_by_uom[product_uom_id.id] = 0
                d_quantity_by_uom[product_uom_id.id] = 0
                
            for product_line_id in doc.product_line_ids.sorted('product_uom_id'):
                service_id = product_line_id.service_id
                product_uom_id = product_line_id.product_uom_id
                description = service_id.name + ' - ' + (product_line_id.product_id.name if product_line_id.product_id else product_line_id.description)
                note = product_line_id.note if product_line_id.note else ""
                
                cur_quants = d_quantity_by_uom.copy()
                cur_quants[product_line_id.product_uom_id.id] = product_line_id.quantity
                res_quant = [list(cur_quant)[1] for cur_quant in cur_quants.items()]

                obj = {
                    "description": description,
                    "uom": product_uom_id.name,
                    "note": note,
                    "quantity": res_quant,
                }
                arr.append(obj)

                for uom_id, quantity in cur_quants.items():
                    quantity_by_uom[uom_id] += quantity

            res_quant = [list(cur_quant)[1] for cur_quant in quantity_by_uom.items()]
            result.update({str(doc.id): {"product_line_ids": arr, "quantity": res_quant}})
        _logger.info(result)
        return result


    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['approval.request'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'approval.request',
            'docs': docs,
            'line_ids': self._get_product_line_ids(docs),
        }
        
    
