{
    'name': "LSF Inherit - documents",
    'version': '19.0.1.0.0',
    'author': 'Dat Nguyen',
    
    'category': 'Hidden',
    'description': """
        Adds advanced viewing modes to the default Odoo 19 List View.
    """,
    'depends': ['web_side_view', 'documents'],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'web_side_view_docs/static/src/*.xml',
        ],
    },
    'license': 'OPL-1',
}
