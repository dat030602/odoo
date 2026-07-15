{
    'name': 'Purchase OCR Extractor CCV',
    'version': '16.0',
    'summary': 'Extract and save customs data (container, seal) from scanned EDO/B/L files',
    'description': '''
This module allows purchase users to upload scanned EDO and Bill of Lading (B/L) PDF files.
It extracts key shipping information using Gemini AI and stores the result as JSON on the Purchase Order.
''',
    'category': 'Purchase',
    'author': 'Leonix',
    'website': 'https://leonix.vn',
    'depends': [
        'purchase_customs_infomation_ccv',
        'base_setup',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/purchase_order_views.xml',
    ],
    'external_dependencies': {
        'python': [
            'google-generativeai',
            'PyMuPDF',
            'pandas',
            'openpyxl',
        ],
    },
    'installable': True,
    'application': True,
    'images': ['static/description/icon.png'],
    'auto_install': False,
    'license': 'LGPL-3',
    'maintainers': ['leonix'],
}
