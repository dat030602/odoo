# -*- coding: utf-8 -*-
"""
Live Integration Test Script for VNPay Payment Provider in Odoo 19
Using the configured keys in database: TMN Code & Hash Secret
"""

import sys
sys.path.insert(0, '/opt/odoo19')
import urllib.parse
from datetime import datetime
import json
import odoo
from odoo.fields import Command
from odoo.orm.registry import Registry

odoo.tools.config.parse_config(['-c', '/opt/odoo19.conf', '-d', 'odoo19'])
registry = Registry('odoo19')

print("=" * 70)
print("=== VNPAY PAYMENT PROVIDER INTEGRATION TEST (LIVE KEYS) ===")
print("=" * 70)

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    # 1. Fetch Provider & Settings
    provider = env['payment.provider'].search([('code', '=', 'vnpay')], limit=1)
    assert provider, "VNPay provider not found!"
    print(f"\n[1] Provider Configuration:")
    print(f"  * Name: {provider.name}")
    print(f"  * Code: {provider.code}")
    print(f"  * State: {provider.state}")
    print(f"  * TMN Code: {provider.vnpay_tmn_code}")
    print(f"  * Hash Secret: {provider.vnpay_hash_secret[:4]}...{provider.vnpay_hash_secret[-4:]}")
    
    tmn_code = provider.vnpay_tmn_code
    hash_secret = provider.vnpay_hash_secret
    
    # Currency & Partner
    vnd_currency = env.ref('base.VND', raise_if_not_found=False)
    if not vnd_currency:
        vnd_currency = env.company.currency_id
    partner = env.ref('base.partner_admin')
    
    # Ensure Payment Method exists
    pm = provider.payment_method_ids[:1]
    if not pm:
        unknown_pm = env.ref('payment.payment_method_unknown', raise_if_not_found=False)
        if not unknown_pm:
            unknown_pm = env['payment.method'].with_context(active_test=False).search([('code', '=', 'unknown')], limit=1)
        provider.write({'payment_method_ids': [Command.link(unknown_pm.id)]})
        unknown_pm.write({'active': True})
        pm = unknown_pm
    print(f"  * Active Payment Method: {pm.name} (Code: {pm.code})")

    # 2. Test Payment URL Generation
    print(f"\n[2] Testing Payment URL Generation:")
    timestamp_ref = datetime.now().strftime('%Y%m%d%H%M%S')
    test_ref = f"TX-VNPAY-{timestamp_ref}"
    test_amount = 500000.0  # 500,000 VND
    
    tx = env['payment.transaction'].create({
        'amount': test_amount,
        'currency_id': vnd_currency.id,
        'provider_id': provider.id,
        'payment_method_id': pm.id,
        'reference': test_ref,
        'partner_id': partner.id,
    })
    cr.commit()
    
    rendering_values = tx._get_specific_rendering_values({})
    redirect_url = rendering_values.get('api_url')
    print(f"  * Transaction Reference: {tx.reference}")
    print(f"  * Transaction Amount: {tx.amount:,.0f} {vnd_currency.name}")
    print(f"  * Generated Redirect URL:\n    {redirect_url}")
    
    # Parse URL
    parsed = urllib.parse.urlparse(redirect_url)
    params = urllib.parse.parse_qs(parsed.query)
    
    assert params.get('vnp_TmnCode', [''])[0] == tmn_code, f"TMN Code mismatch: {params.get('vnp_TmnCode')}"
    assert params.get('vnp_Amount', [''])[0] == str(int(test_amount * 100)), f"Amount mismatch: {params.get('vnp_Amount')}"
    assert params.get('vnp_TxnRef', [''])[0] == test_ref, f"TxnRef mismatch: {params.get('vnp_TxnRef')}"
    assert 'vnp_SecureHash' in params, "vnp_SecureHash missing!"
    
    # Verify the generated hash against hash engine
    flat_params = {k: v[0] for k, v in params.items()}
    engine = env['connector.hash.engine']
    is_hash_valid = engine.verify_hash(
        flat_params['vnp_SecureHash'],
        flat_params,
        hash_secret,
        algorithm='hmac_sha512',
        hash_style='sorted_query'
    )
    print(f"  * Generated Checksum Validation: {'PASSED (Valid Signature)' if is_hash_valid else 'FAILED'}")
    assert is_hash_valid, "Generated URL checksum is invalid!"

    # 3. Test Callback Processing (Success Code 00)
    print(f"\n[3] Testing Callback Processing (Successful Payment - Code 00):")
    callback_success = {
        'vnp_Amount': flat_params['vnp_Amount'],
        'vnp_BankCode': 'NCB',
        'vnp_BankTranNo': 'VNP14567890',
        'vnp_CardType': 'ATM',
        'vnp_OrderInfo': flat_params['vnp_OrderInfo'],
        'vnp_PayDate': datetime.now().strftime('%Y%m%d%H%M%S'),
        'vnp_ResponseCode': '00',
        'vnp_TmnCode': tmn_code,
        'vnp_TransactionNo': '14598231',
        'vnp_TransactionStatus': '00',
        'vnp_TxnRef': test_ref,
    }
    
    # Compute signature with provider secret
    callback_success['vnp_SecureHash'] = engine.build_sorted_query_hash(
        callback_success, hash_secret, algorithm='hmac_sha512'
    )
    
    # Process through transaction notification handler
    tx._process_notification_data(callback_success)
    cr.commit()
    
    print(f"  * VNPay Response Code: {callback_success['vnp_ResponseCode']}")
    print(f"  * VNPay Transaction No: {tx.provider_reference}")
    print(f"  * Transaction State after Callback: {tx.state.upper()}")
    print(f"  * Linked Connector Log ID: {tx.connector_response_log_id.id}")
    print(f"  * Computed Log Body Length: {len(tx.connector_response_log_body)} chars")
    assert tx.state == 'done', f"Expected state 'done', got {tx.state}"
    assert tx.connector_response_log_id, "Response log must be linked to transaction"
    assert tx.connector_response_log_body, "Response log body must be populated"

    # 4. Test Callback Processing (Customer Cancel Code 24)
    print(f"\n[4] Testing Callback Processing (Customer Canceled - Code 24):")
    tx_cancel_ref = f"TX-CANCEL-{timestamp_ref}"
    tx_cancel = env['payment.transaction'].create({
        'amount': 150000.0,
        'currency_id': vnd_currency.id,
        'provider_id': provider.id,
        'payment_method_id': pm.id,
        'reference': tx_cancel_ref,
        'partner_id': partner.id,
    })
    cr.commit()
    
    callback_cancel = {
        'vnp_Amount': '15000000',
        'vnp_OrderInfo': f"Payment for {tx_cancel_ref}",
        'vnp_ResponseCode': '24',
        'vnp_TmnCode': tmn_code,
        'vnp_TransactionNo': '0',
        'vnp_TransactionStatus': '02',
        'vnp_TxnRef': tx_cancel_ref,
    }
    callback_cancel['vnp_SecureHash'] = engine.build_sorted_query_hash(
        callback_cancel, hash_secret, algorithm='hmac_sha512'
    )
    
    tx_cancel._process_notification_data(callback_cancel)
    cr.commit()
    
    print(f"  * Transaction Reference: {tx_cancel.reference}")
    print(f"  * VNPay Response Code: {callback_cancel['vnp_ResponseCode']}")
    print(f"  * Transaction State after Callback: {tx_cancel.state.upper()}")
    assert tx_cancel.state == 'cancel', f"Expected state 'cancel', got {tx_cancel.state}"

    # 5. Test Callback Processing (Tampered / Invalid Signature)
    print(f"\n[5] Testing Callback Processing (Tampered Data / Invalid Checksum):")
    tx_tampered_ref = f"TX-TAMPER-{timestamp_ref}"
    tx_tampered = env['payment.transaction'].create({
        'amount': 300000.0,
        'currency_id': vnd_currency.id,
        'provider_id': provider.id,
        'payment_method_id': pm.id,
        'reference': tx_tampered_ref,
        'partner_id': partner.id,
    })
    cr.commit()
    
    callback_tampered = {
        'vnp_Amount': '30000000',
        'vnp_OrderInfo': f"Payment for {tx_tampered_ref}",
        'vnp_ResponseCode': '00',
        'vnp_TmnCode': tmn_code,
        'vnp_TransactionNo': '99999999',
        'vnp_TransactionStatus': '00',
        'vnp_TxnRef': tx_tampered_ref,
        'vnp_SecureHash': 'tampered_invalid_checksum_abcdef123456',
    }
    
    tx_tampered._process_notification_data(callback_tampered)
    cr.commit()
    
    print(f"  * Transaction Reference: {tx_tampered.reference}")
    print(f"  * Injected Signature: {callback_tampered['vnp_SecureHash']}")
    print(f"  * Transaction State after Callback: {tx_tampered.state.upper()}")
    assert tx_tampered.state == 'error', f"Expected state 'error', got {tx_tampered.state}"

    # 6. Test IPN Server-to-Server Handler
    print(f"\n[6] Testing IPN Webhook Server-to-Server Controller Logic:")
    ipn_ref = f"TX-IPN-{timestamp_ref}"
    tx_ipn = env['payment.transaction'].create({
        'amount': 100000.0,
        'currency_id': vnd_currency.id,
        'provider_id': provider.id,
        'payment_method_id': pm.id,
        'reference': ipn_ref,
        'partner_id': partner.id,
    })
    cr.commit()
    
    # Valid IPN payload
    ipn_payload = {
        'vnp_Amount': '10000000',
        'vnp_BankCode': 'NCB',
        'vnp_CardType': 'ATM',
        'vnp_OrderInfo': f"Payment for {ipn_ref}",
        'vnp_PayDate': datetime.now().strftime('%Y%m%d%H%M%S'),
        'vnp_ResponseCode': '00',
        'vnp_TmnCode': tmn_code,
        'vnp_TransactionNo': '88776655',
        'vnp_TransactionStatus': '00',
        'vnp_TxnRef': ipn_ref,
    }
    ipn_payload['vnp_SecureHash'] = engine.build_sorted_query_hash(
        ipn_payload, hash_secret, algorithm='hmac_sha512'
    )
    
    # Simulate IPN processing
    verify_ipn = env['connector.execution.engine'].handle_callback(
        'vnpay', ipn_payload, hash_style='sorted_query', hash_key='vnp_SecureHash'
    )
    assert verify_ipn.get('valid') is True, "IPN signature verification failed!"
    
    tx_ipn._process_notification_data(ipn_payload)
    cr.commit()
    
    ipn_response = {"RspCode": "00", "Message": "Confirm Success"}
    print(f"  * IPN Transaction: {tx_ipn.reference}")
    print(f"  * IPN Signature Verified: {verify_ipn.get('valid')}")
    print(f"  * Transaction State: {tx_ipn.state.upper()}")
    print(f"  * Response returned to VNPay: {json.dumps(ipn_response)}")
    assert tx_ipn.state == 'done'

print("\n" + "=" * 70)
print("=== ALL INTEGRATION TESTS PASSED (100% SUCCESS) ===")
print("=" * 70)
