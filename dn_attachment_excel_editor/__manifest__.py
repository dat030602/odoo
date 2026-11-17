{
    'name': 'Attachment Excel Editor',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'author': 'Dyan',
    'license': 'LGPL-3',
    'summary': 'In-browser Excel spreadsheet editor for attachment files in many2many_binary widget',
    'images': ['static/description/banner.png'],
    'description': """
Attachment Excel Editor for Odoo 19
===================================
Allows users to open and edit .xlsx and .xlsm file attachments directly within Odoo using the built-in o-spreadsheet engine.

Key Features:
-------------
* Open Excel files (.xlsx / .xlsm) directly from many2many_binary widgets in popup or full-page mode.
* Full spreadsheet capabilities: formulas, styling, multiple sheets, merged cells, images, charts, undo/redo.
* Versioning & Storage options: prompt to overwrite original attachment or create a new copy (v2).
* User preference setting in My Preferences (Ask every time, Always overwrite, Always create new version).
* VBA / macro stripping: .xlsm files are safely stripped of macros and saved as .xlsx.
* Server-side secure decompression and packaging: protects against zip bombs and path traversal.
* Configurable file size limits via ir.config_parameter (dn_attachment_excel_editor.max_file_mb).
* Role-based access control: respects attachment read and write permissions (readonly mode for unprivileged users).
    """,
    'depends': ['web', 'mail', 'spreadsheet'],
    'data': [
        'views/res_users_views.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dn_attachment_excel_editor/static/src/backend/**/*',
        ],
        'spreadsheet.o_spreadsheet': [
            'dn_attachment_excel_editor/static/src/bundle/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
