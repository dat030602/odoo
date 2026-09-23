{
    'name': 'Notification Auto Fetch Record',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Auto fetch/reload record when a notification is displayed',
    'depends': ['web', 'web_studio'],
    'assets': {
        'web.assets_backend': [
            'dn_notification_fetch_record/static/src/form_controller_patch.js',
            'dn_notification_fetch_record/static/src/custom_notification_service.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}

