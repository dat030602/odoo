# -*- coding: utf-8 -*-
"""
Demonstration script for VNPay URL generation and Callback verification
Using generic methods from dn_payment_connector_base logic
"""

import urllib.parse
import hashlib
import hmac
from datetime import datetime

# --- Mocking Engine Logic from dn_payment_connector_base ---

def build_sorted_query_hash(params, secret, algorithm='hmac_sha512', exclude_keys=None):
    exclude = set(exclude_keys or ['vnp_SecureHash', 'vnp_SecureHashType'])
    sorted_keys = sorted(params.keys())
    query_parts = []
    for key in sorted_keys:
        if key in exclude:
            continue
        val = params.get(key)
        if val is not None and str(val) != '':
            encoded_key = urllib.parse.quote_plus(str(key))
            encoded_val = urllib.parse.quote_plus(str(val))
            query_parts.append(f"{encoded_key}={encoded_val}")
            
    hash_data = '&'.join(query_parts)
    secret_bytes = str(secret).encode('utf-8')
    data_bytes = hash_data.encode('utf-8')
    
    if algorithm == 'hmac_sha512':
        return hmac.new(secret_bytes, data_bytes, hashlib.sha512).hexdigest()
    elif algorithm == 'hmac_sha256':
        return hmac.new(secret_bytes, data_bytes, hashlib.sha256).hexdigest()
    return ''

def build_redirect_url(base_url, params, secret, hash_key='vnp_SecureHash'):
    # 1. Calculate hash
    secure_hash = build_sorted_query_hash(params, secret, algorithm='hmac_sha512')
    
    # 2. Build full query string
    parts = []
    for key in sorted(params.keys()):
        val = params[key]
        if val is not None and str(val) != '':
            parts.append(f"{urllib.parse.quote_plus(str(key))}={urllib.parse.quote_plus(str(val))}")
            
    parts.append(f"{urllib.parse.quote_plus(str(hash_key))}={urllib.parse.quote_plus(str(secure_hash))}")
    
    query_string = '&'.join(parts)
    separator = '&' if '?' in base_url else '?'
    return f"{base_url}{separator}{query_string}"

def verify_callback(callback_data, secret, hash_key='vnp_SecureHash'):
    received_hash = callback_data.get(hash_key, '')
    if not received_hash or not secret:
        return False
    expected_hash = build_sorted_query_hash(callback_data, secret, algorithm='hmac_sha512')
    return hmac.compare_digest(str(received_hash).lower(), str(expected_hash).lower())


# --- Run Demo ---

print("=" * 65)
print("=== DEMO: VNPay URL Generation & Callback Verification ===")
print("=" * 65)

# Test / Dummy Credentials (sandbox)
TMN_CODE = "2QXUI4B4"
HASH_SECRET = "RAOCTPUA20CVR0EN4555MPHAZDYGDTWD"
BASE_URL = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"

# 1. Demo URL Generation
tx_ref = "TX-OD19-20261002-001"
amount = 250000.0  # 250,000 VND
vnp_amount = int(amount * 100)  # 25,000,000
now_str = datetime.now().strftime("%Y%m%d%H%M%S")

params = {
    'vnp_Version': '2.1.0',
    'vnp_Command': 'pay',
    'vnp_TmnCode': TMN_CODE,
    'vnp_Amount': vnp_amount,
    'vnp_CurrCode': 'VND',
    'vnp_TxnRef': tx_ref,
    'vnp_OrderInfo': f"Thanh toan don hang {tx_ref}",
    'vnp_OrderType': 'other',
    'vnp_Locale': 'vn',
    'vnp_ReturnUrl': 'http://localhost:8069/payment/vnpay/return',
    'vnp_CreateDate': now_str,
    'vnp_IpAddr': '127.0.0.1',
}

generated_url = build_redirect_url(BASE_URL, params, HASH_SECRET)
print("\n[Step 1] Generated Payment Redirect URL:")
print(generated_url)

# 2. Demo Successful Callback (Response Code 00)
callback_success = dict(params)
callback_success['vnp_ResponseCode'] = '00'
callback_success['vnp_TransactionNo'] = '14598231'
callback_success['vnp_BankCode'] = 'NCB'
callback_success['vnp_PayDate'] = now_str
# VNPay attaches signature
callback_success['vnp_SecureHash'] = build_sorted_query_hash(callback_success, HASH_SECRET)

is_valid = verify_callback(callback_success, HASH_SECRET)
print(f"\n[Step 2] Processing Callback (Success - Code 00):")
print(f"  * Transaction Ref: {callback_success['vnp_TxnRef']}")
print(f"  * VNPay Transaction No: {callback_success['vnp_TransactionNo']}")
print(f"  * Checksum Valid: {is_valid}")
print(f"  * Result State: {'DONE (Payment Successful)' if is_valid and callback_success['vnp_ResponseCode'] == '00' else 'FAILED'}")

# 3. Demo Canceled Callback (Response Code 24)
callback_cancel = dict(params)
callback_cancel['vnp_ResponseCode'] = '24'
callback_cancel['vnp_TransactionNo'] = '0'
callback_cancel['vnp_SecureHash'] = build_sorted_query_hash(callback_cancel, HASH_SECRET)

is_valid_cancel = verify_callback(callback_cancel, HASH_SECRET)
print(f"\n[Step 3] Processing Callback (Customer Cancel - Code 24):")
print(f"  * Checksum Valid: {is_valid_cancel}")
print(f"  * Result State: {'CANCEL (Payment Canceled by User)' if is_valid_cancel and callback_cancel['vnp_ResponseCode'] == '24' else 'FAILED'}")

# 4. Demo Tampered / Invalid Checksum
callback_tampered = dict(callback_success)
callback_tampered['vnp_Amount'] = '50000000'  # Tampered amount!
is_valid_tampered = verify_callback(callback_tampered, HASH_SECRET)
print(f"\n[Step 4] Processing Tampered Callback (Amount altered):")
print(f"  * Checksum Valid: {is_valid_tampered}")
print(f"  * Result State: {'ERROR (Signature Rejected)' if not is_valid_tampered else 'ACCEPTED'}")

print("\n" + "=" * 65)
print("=== DEMO FINISHED SUCCESSFULLY ===")
print("=" * 65)
