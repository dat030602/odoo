# -*- coding: utf-8 -*-
from . import models
from . import report
from odoo.tools import convert_file, exception_to_unicode

def import_csv_data(cr, registry):
    filenames = ['data/hr.payslip.input.type.csv','data/config.salary.insurence.union.dues.csv']

    for filename in filenames:
        convert_file(

            cr, 'biz_payslip_advance',

            filename, None, mode='init', noupdate=True,

            kind='init', pathname=None,
        )

def post_init_import_csv(cr, registry):
    import_csv_data(cr, registry)