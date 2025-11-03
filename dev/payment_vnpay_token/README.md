# VNPay Token Payment Provider

This module provides tokenized payment functionality for VNPay, allowing customers to save their payment methods and reuse them for future transactions.

## Features

- **Token Creation**: Create secure payment tokens for future use
- **Token-based Payments**: Process payments using saved tokens
- **Token Management**: View, update, and delete saved tokens
- **Secure Storage**: Tokens are securely stored and managed
- **API Integration**: Full integration with VNPay Token API

## Installation

1. Copy the module to your Odoo addons directory
2. Update the module list
3. Install the module from the Apps menu

## Configuration

### 1. Provider Setup

1. Go to **Accounting > Configuration > Payment Providers**
2. Find "VNPay Token" and click **Configure**
3. Fill in the required fields:
   - **TMN Code**: Your VNPay merchant code
   - **Hash Secret Key**: Your VNPay secret key
   - **Environment**: Choose between Sandbox and Production

### 2. URL Configuration

The module automatically configures the following URLs:
- **Token Return URL**: `/payment/vnpay_token/token-return/`
- **Token Cancel URL**: `/payment/vnpay_token/token-cancel/`
- **Token Webhook URL**: `/payment/vnpay_token/token-webhook/`

### 3. Environment Settings

- **Sandbox**: For testing with VNPay sandbox environment
- **Production**: For live transactions with VNPay production environment

## Usage

### For Customers

1. **Create a Token**:
   - Go to the payment page
   - Click "Create New Token"
   - You'll be redirected to VNPay to securely save your payment method
   - After successful token creation, you can use it for future payments

2. **Pay with Token**:
   - Select a saved token from the dropdown
   - Enter the payment amount
   - Click "Pay with Token"
   - You'll be redirected to VNPay for payment processing

3. **Manage Tokens**:
   - View your saved tokens
   - Delete tokens you no longer need
   - Update token information

### For Administrators

1. **View All Tokens**:
   - Go to **Accounting > Payment > VNPay Tokens**
   - View all tokens created by customers
   - Monitor token status and usage

2. **Monitor Transactions**:
   - View transaction history
   - Monitor payment status
   - Handle refunds and disputes

## API Endpoints

The module provides the following API endpoints:

- `POST /payment/vnpay_token/create-token/` - Create a new token
- `POST /payment/vnpay_token/delete-token/` - Delete a token
- `POST /payment/vnpay_token/pay-with-token/` - Process payment with token
- `GET /payment/vnpay_token/token-return/` - Handle payment return
- `GET /payment/vnpay_token/token-cancel/` - Handle payment cancellation
- `POST /payment/vnpay_token/token-webhook/` - Handle webhook notifications

## Security

- All tokens are encrypted and securely stored
- API communications use HMAC SHA512 for signature validation
- Webhook notifications are validated for authenticity
- Sensitive data is never exposed in logs

## Troubleshooting

### Common Issues

1. **Token Creation Fails**:
   - Check your TMN Code and Hash Secret Key
   - Verify your environment settings
   - Ensure your return URLs are accessible

2. **Payment Processing Fails**:
   - Verify the token is still valid
   - Check the payment amount and currency
   - Ensure the token belongs to the correct user

3. **Webhook Issues**:
   - Verify your webhook URL is accessible
   - Check the signature validation
   - Ensure your server can receive POST requests

### Logs

Check the Odoo logs for detailed error messages:
- Look for "VNPay Token" in the logs
- Check for API communication errors
- Verify webhook processing

## Support

For technical support:
1. Check the VNPay documentation
2. Review the module logs
3. Contact your system administrator

## License

This module is licensed under LGPL-3.
