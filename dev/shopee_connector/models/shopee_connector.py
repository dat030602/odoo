from odoo import models, fields, _
from odoo.exceptions import ValidationError
import logging
import hmac
import time
import requests
import hashlib
import datetime

_logger = logging.getLogger(__name__)

try:    
    from ...lib import Client
except ImportError:
    Client = None
    _logger.warning("Could not import Client class. Make sure the lib/client.py file exists.")


class ShopeeConnector(models.Model):
    _name = 'shopee.connector'
    _description = 'Shopee Connector'

    # General invoice information
    name = fields.Char(string='Name', required=True, index=True)
    environment = fields.Selection([
        ('sandbox', 'Sandbox'),
        ('production', 'Production'),
    ], string='Environment', required=True, default='sandbox')

    default_partner_id = fields.Many2one('res.partner', string='Default Seller', required=True)
    default_customer_id = fields.Many2one('res.partner', string='Default Customer', required=True)
    default_invoice_partner_id = fields.Many2one('res.partner', string='Default Invoice Partner', required=True)
    default_warehouse_id = fields.Many2one('stock.warehouse', string='Default Warehouse', required=True)
    default_product_promotion_id = fields.Many2one('product.product', string='Default Promotion Product', required=True)
    default_product_shiping_id = fields.Many2one('product.product', string='Default Shipping Product', required=True)
    # default_sale_order_type_id = fields.Many2one('sale.order.type', string='Default Sale Order Type', required=True)
    last_time_run = fields.Datetime(string='Last Run Time')
    access_token = fields.Char(string='Access Token')
    refresh_token = fields.Char(string='Refresh Token')
    time_to_refresh_token = fields.Datetime(string='Token Refresh Time', default=fields.Datetime.now())
    host = fields.Char(string='Host')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
    ], string='Status', required=True, default='draft')
    active = fields.Boolean(string='Active', default=True)

    # Shopee
    shopee_partner_id = fields.Char(string='Partner ID Shopee')
    shopee_partner_key = fields.Char(string='Partner Key Shopee')
    shopee_shop_id = fields.Char(string='Shop ID Shopee')
    shopee_merchant_id = fields.Char(string='Merchant ID Shopee')
    shopee_main_account_id = fields.Char(string='Main Account ID Shopee')
    shopee_shop_name = fields.Char(string='Shop Name Shopee')
    shopee_shop_status = fields.Char(string='Shop Status Shopee')
    shopee_is_main_shop = fields.Boolean(string='Is Main Shop Shopee')

    def action_reset_token(self):
        self.env['shopee.connector'].action_reset_token()

    def action_authen(self):
        return self.env['shopee.connector'].action_authen()

    def action_get_token(self):
        return self.env['shopee.connector'].action_get_token()
    
    def action_get_shop_info(self):
        return self.env['shopee.connector'].action_get_shop_info()

    def action_active(self):
        self.state = 'active'

    def action_draft(self):
        self.state = 'draft'

    def _get_client(self):
        connector = self.env['shopee.connector']
        if Client is None:
            _logger.error("Client class not available. Make sure the lib/client.py file exists.")
            return None
        return Client(connector)

    def _cron_sync_order(self):
        """Create orders from Shopee"""
        return self.env['shopee.connector'].sync_order()

    # HANDLE CONFIG

    def _get_config(self):
        return self.search([], limit=1)

    def _get_url_request(self, path=""):
        timest = int(time.time())
        sign = self._make_sign(path, timest)
        url  = f"{self._get_config().host}{path}?partner_id={self._get_config().shopee_partner_id}&timestamp={timest}&sign={sign}"
        return url

    def _make_sign(self, path: str, timest: int) -> str:
        config = self._get_config()
        base_string = f"{config.shopee_partner_id}{path}{timest}".encode()
        return hmac.new(config.shopee_partner_key.encode(), base_string, hashlib.sha256).hexdigest()

    def action_authen(self):
        config = self._get_config()
        timest = int(time.time())
        path = "/api/v2/shop/auth_partner"
        sign = self._make_sign(path, timest)
        redirect_url = self.get_base_url() + "/marketplace/shopee/auth_callback"
        url = f"{config.host}{path}?partner_id={config.shopee_partner_id}&timestamp={timest}&sign={sign}&redirect={redirect_url}"
        _logger.info("Shopee Auth URL: %s", url)
        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": url,
        }

    def action_get_token(self):
        config = self._get_config()
        if not config.access_token or not config.shopee_shop_id:
            raise ValidationError(_("Please enter Code and Shop ID"))
        timest = int(time.time())
        path = "/api/v2/auth/token/get"
        body = {"code": config.access_token, "shop_id": int(config.shopee_shop_id), "partner_id": int(config.shopee_partner_id)}
        sign = self._make_sign(path, timest)
        url = f"{config.host}{path}?partner_id={config.shopee_partner_id}&timestamp={timest}&sign={sign}"
        resp = requests.post(url, json=body, headers={"Content-Type": "application/json"})
        ret = resp.json()
        config.access_token = ret.get("access_token")
        config.refresh_token = ret.get("refresh_token")
        _logger.info("Shopee access_token=%s, refresh_token=%s", config.access_token, config.refresh_token)
        return ret

    def action_reset_token(self):
        config = self._get_config()
        if not config.refresh_token or not config.shopee_shop_id:
            raise ValidationError(_("No refresh_token or shop_id available"))
        timest = int(time.time())
        path = "/api/v2/auth/access_token/get"
        body = {"shop_id": int(config.shopee_shop_id), "refresh_token": config.refresh_token, "partner_id": int(config.shopee_partner_id)}
        sign = self._make_sign(path, timest)
        url = f"{config.host}{path}?partner_id={config.shopee_partner_id}&timestamp={timest}&sign={sign}"
        resp = requests.post(url, json=body, headers={"Content-Type": "application/json"})
        ret = resp.json()
        config.access_token = ret.get("access_token")
        config.refresh_token = ret.get("refresh_token")
        _logger.info("Shopee new access_token=%s, refresh_token=%s", config.access_token, config.refresh_token)
        return ret

    def action_get_shop_info(self):
        config = self._get_config()
        if not config.access_token:
            raise ValidationError(_("No access_token available. Please perform authentication first."))
        info = self.call_api('shopee_get_shop_info')
        config.shopee_shop_name = info.get("shop_name")
        config.shopee_shop_status = info.get("status")
        config.shopee_is_main_shop = info.get("is_main_shop")
        return info

    # HANDLE API

    def call_api(self, method, **kwargs):
        """
        Call API from Shopee using Shopee class
        """
        config = self._get_config()
        if not config.access_token:
            raise ValidationError(_("No access_token available. Please perform authentication first."))
        
        try:
            client = config._get_client()
            if not client:
                raise ValidationError(_("Cannot initialize Client. Please check lib/client.py file"))

            result = getattr(client, method)(**kwargs)
            _logger.info(f"Successfully called API {method}")
            return result
            
        except NameError as e:
            _logger.error(f"Client method not available: {e}")
            raise ValidationError(_("Client method is not available. Please check lib/client.py file"))
        except Exception as e:
            _logger.error(f"Failed to call API {method}: {e}")
            raise ValidationError(_("Error when calling API {method}: %s") % str(e))


    def _get_all_paginated_data(self, client_method, **kwargs):
        """
        Helper method to get all paginated data from Shopee API
        
        Args:
            client_method: The client method to call (e.g., client.shopee_get_order_list)
            **kwargs: Parameters to pass to the client method
            
        Returns:
            list: All items from all pages
        """
        all_items = []
        cursor = ''
        
        while True:
            # Add cursor to kwargs
            current_kwargs = kwargs.copy()
            current_kwargs['cursor'] = cursor
            
            result = client_method(**current_kwargs)
            
            # Get items based on the method type
            if 'order_list' in result:
                items = result.get('order_list', [])
            elif 'item_list' in result:
                items = result.get('item_list', [])
            else:
                items = []
            
            if not items:
                break
                
            all_items.extend(items)
            _logger.info(f"Retrieved {len(items)} items from page (total: {len(all_items)})")
            
            # Check if there are more pages
            next_cursor = result.get('next_cursor', '')
            if not next_cursor:
                break
                
            cursor = next_cursor
        
        return all_items

    # HANDLE EVENT

    def sync_order(self):
        """
        Create orders from Shopee following sequence:
        1. Get order list from last sync time to current time
        2. Get order details from that list
        3. Search orders, if not exists then create new ones
        """
        config = self._get_config()
        if not config.access_token:
            raise ValidationError(_("No access_token available. Please perform authentication first."))
        
        try:
            # Step 1: Get order list from last sync time to current time
            time_from = config.last_time_run.timestamp() if config.last_time_run else None
            time_to = int(time.time())
            
            _logger.info(f"Getting orders from {time_from} to {time_to}")
            
            # Get all orders with pagination using helper method
            all_orders = self._get_all_paginated_data(
                lambda **kwargs: self.call_api('shopee_get_order_list', **kwargs),
                time_from=time_from,
                time_to=time_to,
                page_size=100
            )
            
            if not all_orders:
                _logger.info("No new orders found")
                return {'message': 'No new orders found'}
            
            order_sn_list = [order['order_sn'] for order in all_orders]
            _logger.info(f"Found {len(order_sn_list)} orders total: {order_sn_list}")
            
            # Step 2: Get order details
            order_detail_result = self.call_api(
                'shopee_get_order_detail',
                order_sn_list=order_sn_list,
                response_optional_fields='buyer_username,item_list'
            )
            
            if not order_detail_result.get('order_list'):
                _logger.warning("No order details found")
                return {'message': 'Order details not found'}
            
            # Step 3: Create orders in Odoo
            created_orders = []
            skipped_orders = []
            
            for order_detail in order_detail_result['order_list']:
                order_sn = order_detail['order_sn']
                
                # Check if order already exists
                existing_order = self.env['sale.order'].search([
                    ('marketplace_name_order', '=', order_sn)
                ], limit=1)
                
                if existing_order:
                    _logger.info(f"Order {order_sn} already exists, skipping")
                    skipped_orders.append(order_sn)
                    continue
                
                # Create new order
                try:
                    new_order = self._create_sale_order(order_detail, config)
                    created_orders.append(new_order.name)
                    _logger.info(f"Created order {new_order.name} for Shopee order {order_sn}")
                except Exception as e:
                    _logger.error(f"Failed to create order for {order_sn}: {e}")
                    continue
            
            # Update last sync time
            config.last_time_run = fields.Datetime.now()
            
            return {
                'message': f'Created {len(created_orders)} new orders, skipped {len(skipped_orders)} existing orders',
                'created_orders': created_orders,
                'skipped_orders': skipped_orders
            }
            
        except Exception as e:
            _logger.error(f"Failed to create orders: {e}")
            raise ValidationError(_("Error when creating orders: %s") % str(e))

    def _fields_to_add_order(self, order_detail):
        return {
            'shopee_payment_method': order_detail.get('payment_method', False),
            'shopee_order_status': order_detail.get('order_status', False),
            'shopee_pay_time': order_detail.get('pay_time', False),
            'shopee_buyer_cancel_reason': order_detail.get('buyer_cancel_reason', False),
            'shopee_cancel_reason': order_detail.get('cancel_reason', False),
            'shopee_total_amount': order_detail.get('total_amount', 0),
            'shopee_full_address': order_detail.get('recipient_address', {}).get('full_address', False),
        }

    def _create_sale_order(self, order_detail, config):
        """Create Sale Order from Shopee order detail"""
        
        # Prepare order data
        pay_time = order_detail.get('pay_time', False)
        if pay_time:
            pay_time = datetime.datetime.fromtimestamp(pay_time)
        order_data = {
            'marketplace_name_order': order_detail['order_sn'],
            'partner_id': config.default_partner_id.id,
            'partner_invoice_id': config.default_invoice_partner_id.id,
            'partner_shipping_id': config.default_customer_id.id,
            'warehouse_id': config.default_warehouse_id.id,
            'state': 'draft',
            'shopee_connector_id': config.id,
            'sale_order_type_id': config.default_sale_order_type_id.id,
            **self._fields_to_add_order(order_detail),
        }
        
        # Create order
        sale_order = self.env['sale.order'].create(order_data)
        
        # Add product lines
        order_lines = []
        for item in order_detail.get('item_list', []):
            # Get Odoo product from mapping
            odoo_product = self.env['shopee.product.mapping'].get_odoo_product(
                str(item['item_id'])
            )
            
            if not odoo_product:
                _logger.warning(f"No mapping found for Shopee item {item['item_id']}: {item['item_name']}")
                # Use default product or skip
                continue
            
            # Create order line
            line_data = {
                'order_id': sale_order.id,
                'product_id': odoo_product.id,
                'product_uom_qty': item['model_quantity_purchased'],
                'price_unit': item['model_discounted_price'],
                'name': item['item_name'],
            }
            
            order_line = self.env['sale.order.line'].create(line_data)
            order_lines.append(order_line)
        
        # Add shipping fee if exists
        if order_detail.get('shipping_fee', 0) > 0:
            shipping_line_data = {
                'order_id': sale_order.id,
                'product_id': config.default_product_shiping_id.id,
                'product_uom_qty': 1,
                'price_unit': order_detail['shipping_fee'],
                'name': 'Shipping fee',
            }
            self.env['sale.order.line'].create(shipping_line_data)
        
        return sale_order

    def sync_product(self):
        """
        Sync products from Shopee following sequence:
        1. Get product list from Shopee
        2. Get product details from that list
        3. Search mapping, if not exists then create new ones
        """
        config = self._get_config()
        if not config.access_token:
            raise ValidationError(_("No access_token available. Please perform authentication first."))
        
        try:
            # Step 1: Get product list from Shopee
            _logger.info("Getting product list from Shopee")
            
            # Get all products with pagination using helper method
            all_items = self._get_all_paginated_data(
                lambda **kwargs: self.call_api('shopee_get_item_list', **kwargs),
                page_size=100,
                item_status='NORMAL'
            )
            
            if not all_items:
                _logger.info("No products found")
                return {'message': 'No products found'}
            
            item_id_list = [item['item_id'] for item in all_items]
            _logger.info(f"Found {len(item_id_list)} products total: {item_id_list}")
            
            # Step 2: Get product details
            item_detail_result = self.call_api(
                'shopee_get_item_base_info',
                item_id_list=item_id_list,
                need_tax_info=True,
                need_complaint_policy=True,
                need_size_chart=True,
                response_optional_fields='item_name,item_sku,item_status,price_info'
            )
            
            if not item_detail_result.get('item_list'):
                _logger.warning("No product details found")
                return {'message': 'Product details not found'}
            
            # Step 3: Create product mappings in Odoo
            created_mappings = []
            skipped_mappings = []
            
            for item_detail in item_detail_result['item_list']:
                item_id = str(item_detail['item_id'])
                
                # Check if mapping already exists
                existing_mapping = self.env['shopee.product.mapping'].search([
                    ('shopee_item_id', '=', item_id)
                ], limit=1)
                
                if existing_mapping:
                    skipped_mappings.append(item_id)
                    continue
                
                # Create new mapping
                try:
                    new_mapping = self._create_product_mapping(item_detail, config)
                    created_mappings.append(new_mapping.shopee_item_id)
                    _logger.info(f"Created product mapping {new_mapping.shopee_item_id} for Shopee item {item_id}")
                except Exception as e:
                    _logger.error(f"Failed to create product mapping for {item_id}: {e}")
                    continue
            
            return {
                'message': f'Created {len(created_mappings)} new product mappings, updated {len(skipped_mappings)} existing mappings',
                'created_mappings': created_mappings,
                'skipped_mappings': skipped_mappings
            }
            
        except Exception as e:
            _logger.error(f"Failed to sync products: {e}")
            raise ValidationError(_("Error when syncing products: %s") % str(e))

    def _create_product_mapping(self, item_detail, config):
        """Create product mapping from Shopee product detail"""
        
        item_id = str(item_detail['item_id'])
        item_name = item_detail.get('item_name', '')
        item_sku = item_detail.get('item_sku', '')
        
        # Find corresponding Odoo product by SKU or name
        odoo_product = None
        
        # Try to find by SKU first
        if item_sku:
            odoo_product = self.env['product.product'].search([
                ('default_code', '=', item_sku)
            ], limit=1)
        
        # If not found by SKU, try to find by name
        if not odoo_product and item_name:
            odoo_product = self.env['product.product'].search([
                ('name', 'ilike', item_name)
            ], limit=1)
        
        # If still not found, use default product (if exists)
        if not odoo_product and hasattr(config, 'default_product_id') and config.default_product_id:
            odoo_product = config.default_product_id
            _logger.warning(f"Using default product for Shopee item {item_id}: {item_name}")
        
        # Create mapping
        mapping_data = {
            'shopee_item_id': item_id,
            'shopee_product_name': item_name,
            'shopee_sku': item_sku,
            'odoo_product_id': odoo_product.id if odoo_product else False,
        }
        
        product_mapping = self.env['shopee.product.mapping'].create(mapping_data)
        
        if not odoo_product:
            _logger.warning(f"Created mapping for Shopee item {item_id} without Odoo product link")
        
        return product_mapping
