from odoo import models, fields, api
import logging
from datetime import datetime
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class CcvDataSrc(models.Model):
    _name = "ccv.data.src"

    name = fields.Char(string="Tên")
    active = fields.Boolean(default=True, string="Hiệu lực (Lưu trữ)")
    single = fields.Char(string="Nội dung")
    multi = fields.Text(string="Nội dung")
    type = fields.Selection(string="Loại", selection=[
        ('single','Văn bản thường'),
        ('multi','Văn bản nhiều dòng'),
    ], default='single')
    picking_type_id = fields.Many2one('stock.picking.type',string="Giao hàng đến")

    @api.model
    def clean_up_transport_methods(self):
        existing = self.with_context(active_test=False).search([('type', '=', 'single')])
        existing.write({'active': False})
        
        allowed_modes = ['CCV vận chuyển', 'Thuê ngoài theo Cont', 'Thuê ngoài theo Xe - Tấn', 'Bao vận chuyển', 'Khác']
        for mode in allowed_modes:
            record = self.with_context(active_test=False).search([('name', '=', mode), ('type', '=', 'single')], limit=1)
            if record:
                record.write({'active': True})
            else:
                self.create({'name': mode, 'type': 'single', 'active': True})
