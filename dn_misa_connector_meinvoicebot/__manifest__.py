# -*- coding: utf-8 -*-
{
    'name': 'MISA meInvoiceBot Connector (INBOT)',
    'version': '19.0.1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Synchronize inbound and outbound e-invoices with MISA INBOT (meInvoiceBot) using decoupled document models.',
    'author': 'Dyan',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'account',
        'dn_misa_connector_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'wizard/misa_inbot_sync_wizard_views.xml',
        'views/misa_inbot_document_views.xml',
        'views/misa_inbot_document_line_views.xml',
        'views/misa_inbot_related_line_views.xml',
        'views/misa_inbot_fee_line_views.xml',
        'views/misa_inbot_zip_downloader_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'description': """
MISA meInvoiceBot Connector (INBOT)
===================================
This module provides seamless synchronization between Odoo and MISA INBOT (meInvoiceBot)
for both inbound (vendor bills) and outbound e-invoices following the Decoupled Document Architecture.

Key Features:
-------------
- Decoupled Document Architecture: Stores complete INBOT e-invoice metadata, ND123, ND70 details,
  and tax/risk checking results in independent intermediate models (misa.inbot.document, misa.inbot.document.line,
  misa.inbot.related.line, misa.inbot.fee.line) without bloating account.move.
- Thin link: Pure Many2one relationship (misa_inbot_id on account.move and move_id on misa.inbot.document).
- Automated Vendor Bill Generation: Converts inbound e-invoices into vendor bills (in_invoice) with automatic
  partner resolution/creation by Tax Code, tax/discount lines, and anti-duplication safeguards.
- Risk and Compliance Gatekeeper: Blocks vendor bill generation if seller is marked as high-risk or inactive (Decree/Tax blacklist).
- Two-way Lifecycle Synchronization:
  * Automatically pushes accounting date (invoiceaccountingdateV2) to INBOT when bills are posted.
  * Automatically pushes payment status (invoicepayment) to INBOT when bills are paid or reconciled.
- Asynchronous ZIP Download & Extraction: Queues bulk ZIP downloads (XML + PDF) and extracts raw files into attachments.
- Scheduled Tasks & Interactive Wizards: Pulls modified invoices automatically via cron or on-demand via sync wizard.
    """,
}
