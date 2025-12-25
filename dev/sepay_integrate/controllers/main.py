# -*- coding: utf-8 -*-
import datetime
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class SePayWebhook(http.Controller):
    """
    SePay Webhook Controller
    According to SePay documentation:
    - Webhook should return {"success": true} with HTTP 200 or 201
    - SePay will retry up to 7 times if webhook fails
    - Need to check for duplicate transactions using transaction ID
    """

    @http.route('/webhook/sepay', type='json', auth='none', methods=['POST'], csrf=False)
    def receive_sepay_payment(self, **post):
        """
        Receive webhook from SePay
        SePay sends transaction data in JSON format
        
        Expected formats:
        1. Full API response: {status: 200, error: null, messages: {...}, transactions: [...]}
        2. Direct transaction list: [{transaction1}, {transaction2}, ...]
        3. Single transaction: {id: ..., account_number: ..., ...}
        """
        try:
            # Get data from SePay (Odoo automatically parses JSON body)
            body = request.jsonrequest
            
            _logger.info(f"SePay webhook received: {body}")
            
            # Check basic data validity
            if not body:
                _logger.error("SePay webhook: Empty request body")
                return {"success": False, "error": "Invalid data format"}
            
            transactions = []
            
            # Handle different webhook payload formats
            if isinstance(body, list):
                # Format 2: Direct transaction list
                transactions = body
            elif isinstance(body, dict):
                if 'transactions' in body:
                    # Format 1: Full API response
                    if body.get('status') != 200:
                        error_msg = body.get('error') or body.get('messages', {}).get('error', 'Unknown error')
                        _logger.error(f"SePay webhook error: {error_msg}")
                        return {"success": False, "error": error_msg}
                    transactions = body.get('transactions', [])
                elif 'id' in body and 'account_number' in body:
                    # Format 3: Single transaction object
                    transactions = [body]
                else:
                    _logger.warning(f"SePay webhook: Unknown payload format: {body}")
                    return {"success": False, "error": "Unknown payload format"}
            
            if not transactions:
                _logger.info("SePay webhook: No transactions in payload")
                return {"success": True, "message": "No transactions to process"}
            
            # Get account.payment model with sudo rights
            payment_model = request.env['account.payment'].sudo()
            
            # Process each transaction
            processed_count = 0
            skipped_count = 0
            error_count = 0
            
            for transaction_data in transactions:
                try:
                    # Check for duplicate using transaction ID
                    transaction_id = transaction_data.get('id')
                    if transaction_id:
                        existing = payment_model.search([
                            ('sepay_transaction_id', '=', str(transaction_id))
                        ], limit=1)
                        
                        if existing:
                            _logger.info(f"SePay: Transaction {transaction_id} already exists, skipping")
                            skipped_count += 1
                            continue
                    
                    # Create payment record
                    payment = payment_model._create_sepay_payment(transaction_data)
                    if payment:
                        processed_count += 1
                        _logger.info(f"SePay: Transaction {transaction_id} processed successfully")
                    else:
                        error_count += 1
                        _logger.warning(f"SePay: Failed to create payment for transaction {transaction_id}")
                        
                except Exception as e:
                    error_count += 1
                    _logger.error(f"SePay: Error processing transaction {transaction_data.get('id')}: {str(e)}")
                    continue
            
            # Return success response (SePay expects {"success": true} with HTTP 200/201)
            _logger.info(f"SePay webhook: Processed {processed_count}, Skipped {skipped_count}, Errors {error_count}")
            return {
                "success": True, 
                "message": f"Processed {processed_count} transactions",
                "processed": processed_count,
                "skipped": skipped_count,
                "errors": error_count
            }
            
        except Exception as e:
            _logger.error(f"SePay webhook error: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
            # Return failure to trigger SePay retry mechanism
            return {"success": False, "error": str(e)}
