from odoo import models, fields, _
from odoo.exceptions import ValidationError
import logging
import hmac
import time
import requests
import hashlib
import datetime
import hmac
import hashlib
from urllib.parse import urlparse
import json

_logger = logging.getLogger(__name__)

try:    
    from ..lib import Client
except ImportError:
    Client = None
    _logger.warning("Could not import Client class. Make sure the lib/client.py file exists.")


class TikTokConnector(models.Model):
    _name = 'tiktok.connector'
    _description = 'TikTok Connector'

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
    default_product_shiping_id = fields.Many2one('product.product', string='Default Shipping Product', required=True)
    last_time_run = fields.Datetime(string='Last Run Time')
    access_token = fields.Char(string='Access Token')
    time_to_refresh_token = fields.Datetime(string='Token Refresh Time', default=fields.Datetime.now())
    host = fields.Char(string='Host')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
    ], string='Status', required=True, default='draft')
    active = fields.Boolean(string='Active', default=True)

    # TikTok
    tiktok_app_key = fields.Char(string='App Key TikTok')
    tiktok_app_secret = fields.Char(string='App Secret TikTok')

    def action_active(self):
        self.state = 'active'

    def action_draft(self):
        self.state = 'draft'

    def _get_client(self):
        connector = self.env['tiktok.connector']
        if Client is None:
            _logger.error("Client class not available. Make sure the lib/client.py file exists.")
            return None
        return Client(connector)

    def _cron_sync_order(self):
        """Create orders from TikTok"""
        return self.env['tiktok.connector'].sync_order()

    # HANDLE CONFIG

    def _get_config(self):
        return self.search([], limit=1)


    def action_authen(self):
        config = self._get_config()
        url = ""
        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": url,
        }

    def action_get_token(self):
        if self.time_to_refresh_token < fields.Datetime.now():
            self.time_to_refresh_token = datetime.datetime.now() + datetime.timedelta(days=1)
            self.access_token = self._make_sign()
        pass
        return

    def action_reset_token(self):
        config = self._get_config()
        return

    # HANDLE API

    def call_api(self, method, **kwargs):
        """
        Call API from TikTok using TikTok class
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
        Helper method to get all paginated data from TikTok API
        
        Args:
            client_method: The client method to call (e.g., client.tiktok_get_order_list)
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
        Create orders from TikTok following sequence:
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
            
            # Get all orders using pagination
            client = config._get_client()
            if not client:
                raise ValidationError(_("Cannot initialize Client. Please check lib/client.py file"))
            
            all_orders = config._get_all_paginated_data(
                client.tiktok_get_order_list,
                time_range_field="create_time",
                time_from=time_from,
                time_to=time_to,
                page_size=100
            )
            
            _logger.info(f"Found {len(all_orders)} orders to process")
            
            # Step 2: Process each order
            for order_data in all_orders:
                try:
                    # Get detailed order information
                    order_detail = client.tiktok_get_order_detail(order_id=order_data.get('order_id'))
                    
                    # Check if order already exists
                    existing_order = self.env['sale.order'].search([
                        ('tiktok_name_order', '=', order_detail.get('order_id'))
                    ], limit=1)
                    
                    if existing_order:
                        _logger.info(f"Order {order_detail.get('order_id')} already exists, skipping")
                        continue
                    
                    # Create new order
                    self._create_order_from_tiktok(order_detail)
                    
                except Exception as e:
                    _logger.error(f"Error processing order {order_data.get('order_id')}: {e}")
                    continue
            
            # Update last sync time
            config.last_time_run = fields.Datetime.now()
            _logger.info("Order sync completed successfully")
            
        except Exception as e:
            _logger.error(f"Error in sync_order: {e}")
            raise ValidationError(_("Error syncing orders: %s") % str(e))

    def _create_order_from_tiktok(self, order_data):
        """
        Create a sale order from TikTok order data
        """
        config = self._get_config()
        
        # Prepare order values
        order_vals = {
            'partner_id': config.default_customer_id.id,
            'tiktok_connector_id': config.id,
            'tiktok_name_order': order_data.get('order_id'),
            'tiktok_full_address': order_data.get('recipient_address', {}).get('full_address', ''),
            'tiktok_order_status': order_data.get('order_status'),
            'tiktok_payment_method': order_data.get('payment_method'),
            'tiktok_pay_time': order_data.get('pay_time'),
            'tiktok_buyer_cancel_reason': order_data.get('buyer_cancel_reason'),
            'tiktok_cancel_reason': order_data.get('cancel_reason'),
            'tiktok_total_amount': order_data.get('total_amount', 0),
            'warehouse_id': config.default_warehouse_id.id,
        }
        
        # Create order lines
        order_lines = []
        for item in order_data.get('item_list', []):
            # Find product mapping
            product_mapping = self.env['tiktok.product.mapping'].get_odoo_product(item.get('item_id'))
            
            if product_mapping:
                product_id = product_mapping.id
            else:
                # Use default product if no mapping found
                product_id = config.default_product_promotion_id.id
                _logger.warning(f"No product mapping found for TikTok item {item.get('item_id')}")
            
            line_vals = {
                'product_id': product_id,
                'product_uom_qty': item.get('quantity', 1),
                'price_unit': item.get('price', 0),
            }
            order_lines.append((0, 0, line_vals))
        
        order_vals['order_line'] = order_lines
        
        # Create the order
        order = self.env['sale.order'].create(order_vals)
        _logger.info(f"Created order {order.name} for TikTok order {order_data.get('order_id')}")
        
        return order
