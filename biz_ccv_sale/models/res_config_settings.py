# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _get_domain_company(self):
        return [('company_id', '=', self.env.company.id)]

    def _get_default_note_sale(self):
        return """
            <p style="margin-bottom: 0px;">Trường hợp Khách hàng chưa thanh toán ngay mà thanh toán trước khi nhận hàng, chúng tôi sẽ áp dụng giá bán tại thời điểm nhận hàng (Do yếu tố biến động giá cả của thị trường).<br></p>
        """

    def _get_default_noted_sale(self):
        return """
            <p style="margin-bottom: 0px;">- Vui lòng fax: 02513.542288, email: kinhdoanh@ccv.vn để xác nhận đơn hàng (có ký tên, đóng dấu).</p>
            <p style="margin-bottom: 0px;">&nbsp;- Mọi thông tin liên hệ: 18006126</p><p style="margin-bottom: 0px;">&nbsp;- Địa chỉ nhận hàng:</p>
            <p style="margin-bottom: 0px;">&nbsp;* Lô 5, đường số 1, KCN Gò Dầu, Phước Thái, Long Thành, Đồng Nai.</p>
            <p style="margin-bottom: 0px;">&nbsp;- Hàng đã đặt vui lòng không đổi hoặc trả lại.</p>
        """

    def _get_default_note_stock(self):
        return """
            Tôi là lái xe đại diện cho bên chủ hàng xác nhận đã kiểm đếm đủ số lượng hàng ghi trên phiếu xuất, toàn bộ số lượng hàng hoá tôi nhận lên xe bao bì sạch đẹp, bao nguyên lành, không ẩm ướt, không đóng cục cứng, không rách bể. Tôi cam kết khi xe ra khỏi kho và nhà máy sẽ không có bất cứ khiếu kiện gì về sau.
        """

    voter_id = fields.Many2one("res.users",string="Voter", domain=_get_domain_company,config_parameter='biz_ccv_sale.voter_id')
    business_department_id = fields.Many2one("res.users",domain=_get_domain_company,string="Business Department", config_parameter='biz_ccv_sale.business_department_id')
    chief_acc_id = fields.Many2one("res.users",string="Chief accountant",domain=_get_domain_company, config_parameter='biz_ccv_sale.chief_acc_id')
    stocker_id = fields.Many2one("res.users",string="Stocker",domain=_get_domain_company, config_parameter='biz_ccv_sale.stocker_id')
    unit_heads_id = fields.Many2one("res.users",string="Unit heads",domain=_get_domain_company, config_parameter='biz_ccv_sale.unit_heads_id')
    driver_consignee_id = fields.Many2one("res.users",string="Driver/Consignee",domain=_get_domain_company, config_parameter='biz_ccv_sale.driver_consignee_id')
    load_department_id = fields.Many2one("res.users",string="Loading and unloading department",domain=_get_domain_company, config_parameter='biz_ccv_sale.load_department_id')
    forklift_id = fields.Many2one("res.users",string="Forklift",domain=_get_domain_company, config_parameter='biz_ccv_sale.forklift_id')
    supervision_department_id = fields.Many2one("res.users",string="Supervision Department",domain=_get_domain_company, config_parameter='biz_ccv_sale.supervision_department_id')

    founder_id = fields.Many2one('res.users', string="Founder", config_parameter='biz_ccv_sale.founder_id')
    regional_head_id = fields.Many2one('res.users', string="Regional Head",
                                       config_parameter='biz_ccv_sale.regional_head_id')
    finance_account_dept_id = fields.Many2one('res.users', string="Finance - Accounting Department",
                                              config_parameter='biz_ccv_sale.finance_account_dept_id')
    sale_manager_id = fields.Many2one('res.users', string="Sales Manager",
                                      config_parameter='biz_ccv_sale.sale_manager_id')
    bod_id = fields.Many2one('res.users', string="Board of Directors", config_parameter='biz_ccv_sale.bod_id')
    internal_control_id = fields.Many2one('res.users', string="Internal control", config_parameter='biz_ccv_sale.internal_control_id')
    delivery_person_id = fields.Many2one('res.users', string="Delivery person", config_parameter='biz_ccv_sale.delivery_person_id')
    protect_service_id = fields.Many2one('res.users', string="Protect service", config_parameter='biz_ccv_sale.protect_service_id')
    carrier_person_id = fields.Many2one('res.users', string="Carrier", config_parameter='biz_ccv_sale.carrier_person_id')
    receipt_chief_accountant_id = fields.Many2one('res.users', string="KTT",
                                                  domain=_get_domain_company,
                                                  config_parameter='biz_ccv_sale.receipt_chief_accountant_id')


    note_sale = fields.Html('Please note', readonly=False, related='company_id.note_sale')
    noted_sale = fields.Html('Noted', readonly=False, related='company_id.noted_sale')
    note_stock = fields.Html('Noted', readonly=False, related='company_id.note_stock')
    