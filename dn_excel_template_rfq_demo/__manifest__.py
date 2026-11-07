# -*- coding: utf-8 -*-
{
    'name': 'Excel Template RFQ Hetian Demo',
    'version': '19.0.1.1.0',
    'category': 'Purchases/Reporting',
    'summary': 'Demonstration and popup print widget for RFQ Hetian Excel template report',
    'description': """
# Excel Template RFQ Hetian Demo & Popup Widget

This module provides demonstration data, extended fields, and an interactive popup preview wizard for the Hetian RFQ Excel Template report.

## Features
- **Hetian RFQ Template Data**: Automatically seeds both Visual Builder and Python Code Script templates (`RFQ Hetian Summary Template` and `RFQ Hetian Python Code Template`).
- **Python Code Execution Support**: Full demonstration of Python code scripting with formatting helpers (`format_date`, `format_amount`, `html2plaintext`) and dynamic table generation.
- **Extended Fields**: Adds missing fields referenced in the template (`x_studio_order_type`, `x_studio_production_country_1`, `x_customer_id`, `conditions`, `order_number`, `design`, `x_studio_material_quality_standards`).
- **Interactive Popup Wizard**: Opens a modal dialog (`excel.template.preview.wizard`) from the RFQ form to preview and download the rendered Excel spreadsheet.
- **Dual Print Actions**: Separate header buttons to test print using Builder mode or Python Code mode directly.
- **OWL 2 Widget**: Custom `excel_preview_popup` button widget embedded on the form.
    """,
    'author': 'Dat Nguyen',
    'website': 'https://github.com/unclecatvn',
    'license': 'LGPL-3',
    'depends': [
        'purchase',
        'dn_excel_template_report',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/excel_template_preview_wizard_views.xml',
        'views/purchase_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dn_excel_template_rfq_demo/static/src/js/excel_preview_widget.js',
            'dn_excel_template_rfq_demo/static/src/xml/excel_preview_widget.xml',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
