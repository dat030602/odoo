{
    'name': 'Crawl Automation Bank',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Crawl Automation Bank data management',
    'description': """
        Crawl Automation Bank data management module
        - Store bank information
        - Manage bank account information
        - Track bank transaction information
    """,
    'author': 'CCV',
    'website': 'https://www.ccv.com.vn',
    'depends': ['account'],
    'data': [
        'views/account_payment.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
