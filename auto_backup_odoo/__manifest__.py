# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Auto Backup Database
#    Copyright (C) 2020 Hilar AK All Rights Reserved
#    https://www.linkedin.com/in/hilar-ak/
#    <hilarak@gmail.com>
#
# Odoo Proprietary License v1.0
#
# This software and associated files (the "Software") may only be used (executed,
# modified, executed after modifications) if you have purchased a valid license
# from the authors, typically via Odoo Apps, or if you have received a written
# agreement from the authors of the Software (see the COPYRIGHT file).
#
# You may develop Odoo modules that use the Software as a library (typically
# by depending on it, importing it and using its resources), but without copying
# any source code or material from the Software. You may distribute those
# modules under the license of your choice, provided that this license is
# compatible with the terms of the Odoo Proprietary License (For example:
# LGPL, MIT, or proprietary licenses similar to this one).
#
# It is forbidden to publish, distribute, sublicense, or sell copies of the Software
# or modified copies of the Software.
#
# The above copyright notice and this permission notice must be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
##############################################################################
{
    'name': "Backup ODOO [Local, Remote, Drive, Dropbox, Amazon S3]",

    'summary': """
        Backup ODOO Using PSQL Dump DB & Filestore Sepeartely in a specified path automatically.
        Automatic Backup, Database in tar, Database in zip, Database in SQL, PSQL restore, Speed restore database,
        table backup, table wise backup, model restore, model backup, Schedule backup, drive backup, google drive backup, dropbox backup,
        amazon backup, s3 backup, reomte backup, sftp backup, local backup
        """,

    'description': """
        This module is for automating the backup process of ODOO databases.
        We are dumping the PSQL database to the proper format defined in the master backup form under general settings.
        This module can deal with the backup of databases more than 1GB and can restore it using pg_restore format.
        The cronjob will do the backup every day and you can change the interval to do the backup process under Automation -> Auto Backup record. 
    """,

    'author': "Hilar AK",
    'website': "https://www.linkedin.com/in/hilar-ak/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'tools',
    'version': '15.1.1.0',
    'license': 'OPL-1',
    'price': 29.99,
    'currency': 'USD',
    'live_test_url': 'https://www.youtube.com/watch?v=7_tjsbOaJSQ',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail'],

    # always loaded
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Views
        'views/views.xml',

        # Scheduler
        'data/scheduler.xml',
    ],
    'images': ["static/images/banner.gif",
               ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo.xml',
    ],
    'external_dependencies': {
        'python': ['pysftp', 'dropbox', 'tqdm', 'boto3', 'botocore', 'simplejson'],
    },
    "pre_init_hook": "pre_init_check",
}
