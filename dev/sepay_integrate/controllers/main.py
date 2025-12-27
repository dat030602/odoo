# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class SePayWebhook(http.Controller):

    @http.route('/webhook/sepay', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_sepay_payment(self, **post):
        try:
            data = request.jsonrequest
            
            if not data:
                _logger.error("SePay Webhook: Request body rỗng")
                return {"success": False, "error": "No data received"}

            _logger.info("SePay Webhook nhận dữ liệu: %s", data)

            # 1. Xác thực API Key (Bảo mật)
            auth_header = request.httprequest.headers.get('Authorization')
            expected_key = request.env['ir.config_parameter'].sudo().get_param('sepay.api_key')
            
            if expected_key and auth_header != f"Apikey {expected_key}":
                _logger.warning("SePay Webhook: Sai API Key hoặc chưa cấu hình")
                return {"success": False, "error": "Invalid API Key"}

            # 2. Chuẩn hóa dữ liệu về danh sách transactions
            transactions = []
            if isinstance(data, list):
                transactions = data
            elif isinstance(data, dict):
                if 'transactions' in data:
                    transactions = data.get('transactions', [])
                elif 'id' in data:
                    transactions = [data]

            if not transactions:
                return {"success": True, "message": "Không có giao dịch để xử lý"}

            payment_model = request.env['account.payment'].sudo()

            # 3. Duyệt và xử lý
            for txn in transactions:
                try:
                    payment_model._create_sepay_payment(txn)
                except Exception:
                    continue

            return {
                "success": True,
            }
        except Exception:
            return {"success": False, "error": "Internal Server Error"}