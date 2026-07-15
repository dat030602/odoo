from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    delivery_note_template = fields.Char(
        string="Delivery Note Template",
        config_parameter='purchase_to_delivery_ccv.delivery_note_template',
        default="Import tons, {product_name}, {container_number}/{seal_number}, STK {custom_declaration_number}, date {custom_declaration_date} - {partner_name}",
        groups='purchase.group_purchase_manager',
    )