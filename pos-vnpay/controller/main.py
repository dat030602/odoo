from odoo import http

import logging
import json
import base64
from urllib.parse import urlparse, parse_qs
from werkzeug.utils import redirect

from odoo.addons.payment_vnpay.static.src.py.vnpay import vnpay as ServiceVNPay
# from pos_vnpay import kanban_image

_logger = logging.getLogger(__name__)

vnpay_service = ServiceVNPay()


class POSVNPayController(http.Controller):

    @staticmethod
    def get_image(product_id):
        product_record = http.request.env['product.product'].browse(
            int(product_id))
        product_image_128_bytes = product_record.image_128

        # Encode the image bytes to base64
        base64_encoded_image = base64.b64encode(
            product_image_128_bytes).decode('utf-8')

        # Construct the URL
        image_url = "/web/image?model=product.product&field=image_128&id={}&unique={}".format(
            product_id, base64_encoded_image)

        return image_url

    ###############################

    payment_client = '/pos_vnpay/payment-client'

    @http.route(payment_client, auth='user', type='json', website=True)
    def payment_client_page(self):
        records = http.request.env['pos_vnpay.stack_payment'].search(
            [('status_order', '=', 'waiting')], limit=1)

        detail_order = json.loads(records.detail_order)
        products_paid = detail_order['product_paid']
        # product.product
        # image_128
        for product_paid in products_paid:
            image = self.get_image(int(product_paid['id']))
            product_paid['img'] = image

        detail_order['product_paid'] = products_paid

        return json.dumps({
            'order_id': records.order_id,
            'vnp_TxnRef': records.vnp_TxnRef,
            'vnp_OrderInfo': records.vnp_OrderInfo,
            'detail_order': json.dumps(detail_order),
            'qr_code': records.qr_code
        })

    ##################

    _payment_progess = '/payment/pos-vnpay/payment-return/'

    @http.route(_payment_progess)
    def pos_vnpay_payment_return(self):
        try:
            url = http.request.httprequest.url

            parsed_url = urlparse(url)

            keyPayment = http.request.env['payment.provider'].sudo().search(
                [('code', '=', 'vnpay')])

            params = {'vnp_TxnRef': parse_qs(parsed_url.query)['vnp_TxnRef'][0],
                      'vnp_Amount': int(parse_qs(parsed_url.query)['vnp_Amount'][0]),
                      'vnp_OrderInfo': parse_qs(parsed_url.query)['vnp_OrderInfo'][0],
                      'vnp_TransactionNo': parse_qs(parsed_url.query)['vnp_TransactionNo'][0],
                      'vnp_ResponseCode': parse_qs(parsed_url.query)['vnp_ResponseCode'][0],
                      'vnp_TmnCode': parse_qs(parsed_url.query)['vnp_TmnCode'][0],
                      'vnp_PayDate': parse_qs(parsed_url.query)['vnp_PayDate'][0],
                      'vnp_BankCode': parse_qs(parsed_url.query)['vnp_BankCode'][0],
                      'vnp_CardType': parse_qs(parsed_url.query)['vnp_CardType'][0],
                      'vnp_BankTranNo': parse_qs(parsed_url.query)['vnp_BankTranNo'][0],
                      'vnp_TransactionStatus': parse_qs(parsed_url.query)['vnp_TransactionStatus'][0],
                      'vnp_SecureHash': parse_qs(parsed_url.query)['vnp_SecureHash'][0]}
            status = ''
            if vnpay_service.validate_response(keyPayment['vnpay_hash_secret_key'], params):

                if params['vnp_ResponseCode'] == "00":
                    status = 'done'
                else:
                    status = 'canceled'
            else:
                status = 'canceled'

            orders = http.request.env['pos_vnpay.stack_payment'].search(
                [('vnp_TxnRef', '=', params['vnp_TxnRef'])])

            for order in orders:
                order.write({'status_order': status})

            return redirect(self.window_close_url)
        except:
            _logger.error("Lỗi thanh toán")
            return redirect(self.window_close_url)

    ####################################

    window_close_url = '/window-close'

    @http.route(window_close_url, type='http', auth='user')
    def your_controller_method(self, **kwargs):
        return """
            <script type="text/javascript">
                window.close();
            </script>
        """

        ###############################

    orderline = '/pos/orderline'

    @http.route(orderline, auth='user', type='json', website=True)
    def handle_orderline(self):
        records = http.request.env['pos_vnpay.stack_payment'].search(
            [('status_order', '=', 'waiting')], limit=1)

        detail_order = json.loads(records.detail_order)
        products_paid = detail_order['product_paid']

        for product_paid in products_paid:
            image = self.get_image(int(product_paid['id']))
            product_paid['img'] = image

        detail_order['product_paid'] = products_paid

        return json.dumps({
            'order_id': records.order_id,
            'vnp_TxnRef': records.vnp_TxnRef,
            'vnp_OrderInfo': records.vnp_OrderInfo,
            'detail_order': json.dumps(detail_order),
            'qr_code': records.qr_code
        })

    ###############

    update_qr_code = '/pos-qr-code'

    @http.route(update_qr_code, type='json', auth='public', methods=['POST'], cors='*', csrf=False)
    def update_qr_code_method(self, **kwargs):
        request_body = http.request.httprequest.data

        # If your data is in JSON format, you can parse it
        json_data = json.loads(request_body)

        # Process the JSON data as needed
        url = json_data.get('q', None)
        id = json_data.get('id', None)

        # Updating records in the 'pos_vnpay.stack_payment' model
        orders = http.request.env['pos_vnpay.stack_payment'].sudo().search(
            [('trading_code', '=', id)])
        for order in orders:
            order.sudo().write({'qr_code': url})

        return json.dumps({"Yourresponse": "Your response"})
    
    demo = '/test'

    @http.route(demo, type='json', auth='public', methods=['GET'], cors='*', csrf=False)
    def demo_method(self, **kwargs):
        return json.dumps({"Yourresponse": "Your response"})
