{
    'name': "Duplicate Customer Detection",
    'summary': "Detect and prevent duplicate customer entries",
    'description': """
This module provides functionality to detect and prevent duplicate customer entries in the system. It helps maintain data integrity by ensuring that each customer is unique based on specified criteria such as email, phone number, or other identifiers. The module can be configured to automatically check for duplicates when creating or updating customer records, and it can provide suggestions for merging duplicate entries.
    """,
    'author': 'Dat Nguyen',
    
    'category': 'Hidden',
    'version': '19.0.1.0.1',
    'license': 'OPL-1',
    'depends': ['sale','purchase','account','crm','contacts'],
    'data': [
        'views/account_move.xml',
        'views/res_partner.xml',
        'views/sale_order.xml',
        'views/purchase_order.xml',
        'views/crm_lead.xml',
    ],
    'installable': True,
    'application': False,
}
