# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
import json

_logger = logging.getLogger(__name__)

class SePayWebhook(http.Controller):

    @http.route('/webhook/sepay', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_sepay_payment(self, **post):
        try:
            try:
                body = json.loads(request.httprequest.data.decode('utf-8'))
            except Exception:
                return {
                    "error": 1,
                    "message": "Invalid JSON body"
                }

            if body.get('error') != 0:
                return {
                    "error": 1,
                    "message": "Invalid data format"
                }
            
            _logger.info("SePay Webhook nhận dữ liệu: %s", json.dumps(body, indent=2, ensure_ascii=False))

            # 1. Xác thực API Key (Bảo mật)
            auth_header = request.httprequest.headers.get('Authorization')
            expected_key = request.env['ir.config_parameter'].sudo().get_param('sepay.api_key')
            
            if expected_key and auth_header != f"Apikey {expected_key}":
                _logger.warning("SePay Webhook: Sai API Key hoặc chưa cấu hình")
                return {"success": False, "error": "Invalid API Key"}

            # 2. Chuẩn hóa dữ liệu về danh sách transactions
            transactions = []
            if isinstance(body, list):
                transactions = body
            elif isinstance(body, dict):
                if 'transactions' in body:
                    transactions = body.get('transactions', [])
                elif 'transaction' in body:
                    transactions = [body.get('transaction', {})]
                elif 'id' in body:
                    transactions = [body]

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
        except Exception as e:
            return {"success": False, "error": str(e)}