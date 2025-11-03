from odoo import models, fields
import datetime
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tiktok_connector_id = fields.Many2one('tiktok.connector', string='TikTok', readonly=True)
    tiktok_name_order = fields.Char(string='Order Code', readonly=True)

    # TikTok
    tiktok_full_address = fields.Char(string='Full Address', readonly=True)
    tiktok_order_status = fields.Selection(string='Order Status', selection=[
        ('UNPAID', 'Unpaid'),
        ('READY_TO_SHIP', 'Ready to Ship'),
        ('PROCESSED', 'Processed'),
        ('SHIPPED', 'Shipped'),
        ('COMPLETED', 'Completed'),
        ('IN_CANCEL', 'In Cancel'),
        ('CANCELLED', 'Cancelled'),
        ('INVOICE_PENDING', 'Invoice Pending'),
    ], readonly=True)
    tiktok_payment_method = fields.Selection(string='Payment Method', selection=[
        ('Credit Card', 'Credit Card'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Cash on Delivery', 'Cash on Delivery'),
        ('TikTok Wallet', 'TikTok Wallet'),
        ('Buyer-Seller Self Arrange', 'Buyer-Seller Self Arrange'),
    ], readonly=True)
    tiktok_pay_time = fields.Datetime(string='Payment Time', readonly=True)
    tiktok_buyer_cancel_reason = fields.Char(string='Buyer Cancel Reason', readonly=True)
    tiktok_cancel_reason = fields.Char(string='Cancel Reason', readonly=True)
    tiktok_total_amount = fields.Monetary(string='Total Amount', readonly=True)

    def _cron_done_sale_order(self):
        orders = self.search([('tiktok_connector_id', '!=', False), ('state', 'not in', ['cancel', 'done'])])
        for order in orders:
            if order.tiktok_connector_id:
                # Confirm order
                if order.state == 'draft':
                    order.action_confirm()
                order.action_launch_stock_rule()
                picking_ids = order.picking_ids.filtered(lambda x: x.state == 'draft')
                picking_ids.action_confirm()
                picking_ids.action_assign()
                picking_ids.move_ids._set_quantities_to_reservation()
                picking_ids.with_context(skip_immediate=True, manual_validate_date_time=datetime.datetime.now()).button_validate()
                order.action_done()

                # Send invoice
                for invoice in order.invoice_ids:
                    if not invoice.sinvoice_ids:
                        invoice.action_create_data_sinvoice()
                        invoice.sinvoice_ids.write({
                            'payment_method': '3',
                        })
                        invoice.sinvoice_ids.action_confirm()
                        invoice.sinvoice_ids.action_create_invoice()
