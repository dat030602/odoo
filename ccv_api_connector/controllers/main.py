from odoo import http
from odoo.http import request

import json

class NpkWeighingController(http.Controller):
    
    @http.route('/api/confirm_npk_weighing', type='http', auth='public', methods=['POST'], csrf=False)
    def api_confirm_npk_weighing(self, **kwargs):
        """
        API Endpoint hứng dữ liệu từ máy cân
        URL: http://<ip>:<port>/api/confirm_npk_weighing
        """
        try:
            # Lấy dữ liệu từ payload JSON (dạng raw)
            data = json.loads(request.httprequest.data)
        except Exception:
            return request.make_response(json.dumps({'status': 'error', 'message': 'Invalid JSON format'}), headers=[('Content-Type', 'application/json')])

        ticket_name = data.get('ticket_name')
        ma_nha_may = data.get('ma_nha_may')
        ma_can = data.get('ma_can')
        vals = data.get('vals', {})

        if not ticket_name:
            return request.make_response(json.dumps({'status': 'error', 'message': 'Thiếu tham số ticket_name'}), headers=[('Content-Type', 'application/json')])

        # Gọi hàm trong model npk.weighing.history với quyền sudo (bỏ qua bắt buộc đăng nhập)
        success = request.env['npk.weighing.history'].sudo().api_confirm_npk_weighing(
            ticket_name=ticket_name, 
            ma_nha_may=ma_nha_may, 
            ma_can=ma_can, 
            vals=vals
        )
        
        if success:
            return request.make_response(json.dumps({'status': 'success', 'message': f'Đã cập nhật thành công phiếu {ticket_name}'}), headers=[('Content-Type', 'application/json')])
        else:
            return request.make_response(json.dumps({'status': 'error', 'message': f'Không tìm thấy phiếu cân {ticket_name} hoặc có lỗi xảy ra'}), headers=[('Content-Type', 'application/json')])

