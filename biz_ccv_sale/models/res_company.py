# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import base64

from odoo import api, fields, models, tools, _, Command


class Company(models.Model):
    _inherit = "res.company"

    # def _get_header_image(self):
    #     return base64.b64encode(open(os.path.join(tools.config['root_path'].replace('/odoo', '/'), 'develop', 'biz_ccv_sale', 'static', 'img', 'res_company_header_report.jpg'), 'rb') .read())

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
            <p>Tôi là lái xe đại diện cho bên chủ hàng xác nhận đã kiểm đếm đủ số lượng hàng ghi trên phiếu xuất, toàn bộ số lượng hàng hoá tôi nhận lên xe bao bì sạch đẹp, bao nguyên lành, không ẩm ướt, không đóng cục cứng, không rách bể. Tôi cam kết khi xe ra khỏi kho và nhà máy sẽ không có bất cứ khiếu kiện gì về sau.</p>
        """

    header_image = fields.Binary(string="Header Report", readonly=False)
    note_sale = fields.Html('Please note', default=_get_default_note_sale)
    noted_sale = fields.Html('Noted', default=_get_default_noted_sale)
    note_stock = fields.Html('Noted', default=_get_default_note_stock)

