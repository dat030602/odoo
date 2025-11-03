# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from urllib.parse import urlparse, parse_qs
from werkzeug.utils import redirect

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class VNPayController(http.Controller):
    """Controller for handling VNPay payment notifications and returns."""

    # VNPay response code mapping based on official documentation
    RESPONSE_CODE_MAPPING = {
        '00': 'paid',      # Giao dịch thành công
        '07': 'paid',      # Trừ tiền thành công. Giao dịch bị nghi ngờ (liên quan tới lừa đảo, giao dịch bất thường)
        '09': 'failed',    # Giao dịch không thành công do: Thẻ/Tài khoản của khách hàng chưa đăng ký dịch vụ InternetBanking
        '10': 'failed',    # Giao dịch không thành công do: Khách hàng xác thực thông tin thẻ/tài khoản không đúng quá 3 lần
        '11': 'failed',    # Giao dịch không thành công do: Đã hết hạn chờ thanh toán
        '12': 'failed',    # Giao dịch không thành công do: Thẻ/Tài khoản của khách hàng bị khóa
        '13': 'failed',    # Giao dịch không thành công do Quý khách nhập sai mật khẩu xác thực giao dịch (OTP)
        '24': 'canceled',  # Giao dịch không thành công do: Khách hàng hủy giao dịch
        '51': 'failed',    # Giao dịch không thành công do: Tài khoản của quý khách không đủ số dư
        '65': 'failed',    # Giao dịch không thành công do: Tài khoản của Quý khách đã vượt quá hạn mức giao dịch trong ngày
        '75': 'failed',    # Ngân hàng thanh toán đang bảo trì
        '79': 'failed',    # Giao dịch không thành công do: KH nhập sai mật khẩu thanh toán quá số lần quy định
        '99': 'failed',    # Các lỗi khác (lỗi còn lại, không có trong danh sách mã lỗi đã liệt kê)
    }
    
    # VNPay transaction status mapping
    TRANSACTION_STATUS_MAPPING = {
        '00': 'paid',      # Giao dịch thành công
        '01': 'pending',   # Giao dịch chưa hoàn tất
        '02': 'failed',    # Giao dịch bị lỗi
        '04': 'pending',   # Giao dịch đảo (Khách hàng đã bị trừ tiền tại Ngân hàng nhưng GD chưa thành công ở VNPAY)
        '05': 'pending',   # VNPAY đang xử lý giao dịch này (GD hoàn tiền)
        '06': 'pending',   # VNPAY đã gửi yêu cầu hoàn tiền sang Ngân hàng (GD hoàn tiền)
        '07': 'failed',    # Giao dịch bị nghi ngờ gian lận
        '09': 'failed',    # GD Hoàn trả bị từ chối
    }

    @http.route('/payment/vnpay/payment-return/', type='http', auth='public', csrf=False)
    def vnpay_payment_return(self):
        """Handle VNPay payment return callback."""
        try:
            # Extract and validate parameters from URL
            params = self._extract_url_parameters()
            if not params or not params.get('vnp_TxnRef'):
                _logger.error("VNPay: Missing required parameters in payment return")
                return self._redirect_to_payment_status('')

            # Get VNPay provider
            provider = self._get_vnpay_provider()
            if not provider:
                _logger.error("VNPay: Provider not found")
                return self._redirect_to_payment_status('')

            # Determine payment status
            status = self._determine_payment_status(params, provider)
            
            # Handle transaction notification
            self._handle_transaction_notification(params['vnp_TxnRef'], status)
            
            return self._redirect_to_payment_status(status)

        except (ValueError, TypeError) as e:
            _logger.error("VNPay: Invalid parameter format - %s", str(e))
            return self._redirect_to_payment_status('')
        except Exception as e:
            _logger.error("VNPay: Payment processing error - %s", str(e))
            return self._redirect_to_payment_status('')

    def _extract_url_parameters(self):
        """Extract and validate parameters from the request URL."""
        try:
            url = request.httprequest.url
            parsed_url = urlparse(url)
            query_dict = parse_qs(parsed_url.query)
            
            # Extract parameters with validation
            params = {
                'vnp_TxnRef': self._get_first_param(query_dict, 'vnp_TxnRef'),
                'vnp_Amount': self._safe_int_conversion(query_dict.get('vnp_Amount', ['0'])[0]),
                'vnp_OrderInfo': self._get_first_param(query_dict, 'vnp_OrderInfo'),
                'vnp_TransactionNo': self._get_first_param(query_dict, 'vnp_TransactionNo'),
                'vnp_ResponseCode': self._get_first_param(query_dict, 'vnp_ResponseCode'),
                'vnp_TmnCode': self._get_first_param(query_dict, 'vnp_TmnCode'),
                'vnp_PayDate': self._get_first_param(query_dict, 'vnp_PayDate'),
                'vnp_BankCode': self._get_first_param(query_dict, 'vnp_BankCode'),
                'vnp_CardType': self._get_first_param(query_dict, 'vnp_CardType'),
                'vnp_BankTranNo': self._get_first_param(query_dict, 'vnp_BankTranNo'),
                'vnp_TransactionStatus': self._get_first_param(query_dict, 'vnp_TransactionStatus'),
                'vnp_SecureHash': self._get_first_param(query_dict, 'vnp_SecureHash'),
            }
            
            return params
        except Exception as e:
            _logger.error("VNPay: Error extracting URL parameters - %s", str(e))
            return None

    def _get_first_param(self, query_dict, key):
        """Safely get the first parameter value from query dictionary."""
        values = query_dict.get(key, [''])
        return values[0] if values else ''

    def _safe_int_conversion(self, value):
        """Safely convert string to integer."""
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0

    def _get_vnpay_provider(self):
        """Get VNPay payment provider."""
        try:
            return request.env['payment.provider'].sudo().search([('code', '=', 'vnpay')], limit=1)
        except Exception as e:
            _logger.error("VNPay: Error getting provider - %s", str(e))
            return None

    def _determine_payment_status(self, params, provider):
        """Determine payment status based on response code and validation."""
        try:
            # Validate response if provider supports it
            if hasattr(provider, 'validate_response') and not provider.validate_response(params):
                _logger.warning("VNPay: Response validation failed for transaction %s", params.get('vnp_TxnRef', ''))
                return ''

            response_code = params.get('vnp_ResponseCode', '')
            transaction_status = params.get('vnp_TransactionStatus', '')
            
            # Priority: Response code first, then transaction status
            if response_code in self.RESPONSE_CODE_MAPPING:
                status = self.RESPONSE_CODE_MAPPING[response_code]
                _logger.info("VNPay: Using response code %s -> status %s", response_code, status)
                return status
            elif transaction_status in self.TRANSACTION_STATUS_MAPPING:
                status = self.TRANSACTION_STATUS_MAPPING[transaction_status]
                _logger.info("VNPay: Using transaction status %s -> status %s", transaction_status, status)
                return status
            else:
                _logger.warning("VNPay: Unknown response code %s and transaction status %s", response_code, transaction_status)
                return 'canceled'
            
        except Exception as e:
            _logger.error("VNPay: Error determining payment status - %s", str(e))
            return ''

    def _handle_transaction_notification(self, reference, status):
        """Handle transaction notification data."""
        try:
            request.env['payment.transaction'].sudo()._handle_notification_data(
                'vnpay', 
                {'reference': reference, 'status': status}
            )
        except Exception as e:
            _logger.error("VNPay: Error handling transaction notification - %s", str(e))

    @http.route('/payment/vnpay/webhook/', type='http', auth='public', csrf=False, methods=['POST'])
    def vnpay_webhook(self):
        """Handle VNPay webhook notifications."""
        try:
            # Extract parameters from POST data
            params = request.httprequest.form.to_dict()
            if not params or not params.get('vnp_TxnRef'):
                _logger.error("VNPay: Missing required parameters in webhook")
                return "Missing parameters", 400

            # Get VNPay provider
            provider = self._get_vnpay_provider()
            if not provider:
                _logger.error("VNPay: Provider not found in webhook")
                return "Provider not found", 400

            # Validate webhook signature
            if not provider.validate_response(params):
                _logger.warning("VNPay: Webhook validation failed for transaction %s", params.get('vnp_TxnRef', ''))
                return "Invalid signature", 400

            # Determine payment status
            status = self._determine_payment_status(params, provider)
            
            # Handle transaction notification
            self._handle_transaction_notification(params['vnp_TxnRef'], status)
            
            return "OK", 200

        except Exception as e:
            _logger.error("VNPay: Webhook processing error - %s", str(e))
            return "Internal error", 500

    def _redirect_to_payment_status(self, status):
        """Redirect to payment status page."""
        return redirect('/payment/status')
