# -*- coding: utf-8 -*-
{
    'name': 'VNPay Payment Provider',
    'version': '1.0.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': 'VNPay payment gateway integration via DN Payment Connector Base',
    'description': """
        VNPay Payment Gateway Integration
        =================================
        Integrates VNPay Payment Gateway with Odoo 19 Payment Framework.
        Built on top of dn_payment_connector_base.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'payment',
        'dn_payment_connector_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/vnpay_connector_data.xml',
        'views/payment_vnpay_templates.xml',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'data/vnpay_payment_data.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
