# -*- coding: utf-8 -*-
{
    'name': 'Vietnam Accounting - Flexible Mixed Account Usage',
    'version': '19.0.1.1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Allow flexible usage of receivable and payable accounts across document types',
    'description': """
Vietnam Accounting - Flexible Mixed Account Usage
=================================================
Allows flexible usage of receivable and payable accounts across document types,
designed for Vietnamese Accounting Standards (VAS Circular 200/2014/TT-BTC) and
multi-journal operations.

Key Features & Use Cases
------------------------
* **Account 141 (Employee Advances):**
  Allows tracking employee advances using receivable/payable mechanics without
  getting blocked by Odoo's default document-type constraints in cash, bank, or
  vendor bill journals.
* **Accounts 131 & 331 (Prepayments & Offsetting):**
  Enables direct clearing and offsetting between customer receivables and vendor
  payables across miscellaneous journals and documents.
* **Document Constraint Bypass:**
  Bypasses the strict `_check_payable_receivable()` restriction only on accounts
  explicitly configured with "Allow Mixed Usage".
* **Native Integrity:**
  Retains 100% native reconciliation, partner ledger accuracy, aged balance
  reporting, and currency exchange mechanisms.

Configuration
-------------
1. Navigate to **Accounting > Configuration > Chart of Accounts**.
2. Open an account (e.g. Account 141, 131, or 331).
3. Enable the **Allow Mixed Usage** toggle.
4. Save and record transactions freely across journals.
    """,
    'author': 'Dyan',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/account_account_views.xml',
        'views/account_move_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
