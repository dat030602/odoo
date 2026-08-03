{
    'name'        : 'Sale Excel Report',
    'version'     : '19.0.1.0.0',
    'category'    : 'Sales',
    'summary'     : '',
    'description' : "",
    'author'   : 'Dat Nguyen',
    'depends'  : ['dn_excel_report_base', 'sale_management'],
    'data'     : [
        'security/ir.model.access.csv',
        'views/sale_excel_report.xml',
    ],
    'installable'  : True,
    'application'  : False,
    'auto_install' : False,
    'license'      : 'LGPL-3',
}
