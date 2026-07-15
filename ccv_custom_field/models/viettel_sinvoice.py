from odoo import models, fields, api
import logging
from odoo.exceptions import UserError,ValidationError

_logger = logging.getLogger(__name__)


class ViettelSinvoice(models.Model):
    _inherit = "viettel.sinvoice"

    partner_identity_card = fields.Char(string="Mã định danh")
    use_identity_card = fields.Selection(string='Xuất hóa đơn', selection=[
        ('vat','Mã số thuế'),
        ('id','Căn cước công dân'),
    ],default='vat')
    payment_method = fields.Selection(string="Hình thức thanh toán",selection=[
        ('2','CK'),
        ('3','TM/CK'),
        ('1','TM'),
        ('4','DTCN'),
        ('5','KHAC'),],default='2',required=True)
    
    @api.onchange('partner_vat_id')    
    def change_id_partner_vat(self):
        res = super(ViettelSinvoice,self).change_id_partner_vat()
        if self.partner_vat_id:
            if self.use_identity_card == 'vat':
                self.partner_vat = self.partner_vat_id.vat or ''
                self.partner_identity_card = ''
            else:
                self.partner_vat = ''
                self.partner_identity_card = self.partner_vat_id.identity_card or ''
        return res

    def action_confirm(self):
        # if (self.use_identity_card == 'vat' and not self.partner_vat) \
        #         or (self.use_identity_card == 'id' and not self.partner_identity_card) \
        #         or not self.partner_vat_address:
        #     raise ValidationError('Thông tin khách hàng bị thiếu, Vui lòng kiểm tra lại !!!')
        self.write({'state':'comfirm'})

    def get_buyerInfo(self):
        buyerInfo = super(ViettelSinvoice,self).get_buyerInfo()
        if self.use_identity_card == 'id':
            buyerInfo.update({"buyerIdType": '1',"buyerIdNo": self.partner_identity_card,"buyerTaxCode": ''})
        return buyerInfo
    
    def get_payments(self):
        payment_method_dict = dict(self._fields['payment_method'].selection)
        payment_method_name = payment_method_dict.get(self.payment_method, '')
        return [{
            "paymentMethod": self.payment_method,
            "paymentMethodName": payment_method_name,
        }]
