# -*- coding: utf-8 -*-
{
    'name': 'MISA meInvoice Connector',
    'version': '19.0.1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Electronic invoice, receipt, and stock delivery note issuance connector for MISA meInvoice',
    'description': """
MISA meInvoice Connector
========================

This module provides e-Invoice issuance, replacement, adjustment, and preview features integrated with MISA meInvoice:
- Decoupled document architecture (`misa.einvoice.document`, `misa.einvoice.document.line`, `misa.einvoice.tax.line`).
- Thin link integration with Odoo standard models: Invoices (`account.move`), POS Orders (`pos.order`), and Stock Delivery Orders (`stock.picking`).
- Synchronization of Invoice Templates (`misa.invoice.template`) and Digital Certificates (`misa.certificate`).
- InvSeries parsing (Invoice type, CQT code status, invoice format like cash register or normal).
- Replacement and adjustment document workflows with 14 reason codes according to Circular 91 Appendix XVII.
- Support for 3 digital signing flows: USB Token / Soft file (SignType 1), HSM / Cloud eSign (SignType 2), and Cash Register / POS (SignType 5).
- 5-minute unpublish preview wizard and draft invoice handling.
- Extended domain fields for Stock Delivery Notes (PXK), Automobile / Vehicle details (chassis, engine, license plate), Lot / Expiry tracking, and Utility / Hospitality meters.
    """,
    'author': 'Dyan',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'account',
        'stock',
        'point_of_sale',
        'dn_misa_connector_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/misa_invoice_template_views.xml',
        'views/misa_certificate_views.xml',
        'views/misa_einvoice_document_views.xml',
        'views/misa_einvoice_document_line_views.xml',
        'views/misa_einvoice_tax_line_views.xml',
        'views/account_move_views.xml',
        'views/pos_order_views.xml',
        'views/stock_picking_views.xml',
        'wizard/misa_einvoice_preview_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
