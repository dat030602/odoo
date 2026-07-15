# -*- coding: utf-8 -*-
{

    'name': 'Product Image in Sale order and Invoice',
    "author": "Edge Technologies",
    'version': '16.0.1.1',
    'live_test_url': "https://youtu.be/aUpLwh6hQJI",
    "images":['static/description/main_screenshot.png'],
    'summary': "Sale product image in sale order lines invoice product image in invoice order lines so line product image sale order product image on sale order line image print product image on sale report print product image on invoice report product image in invoice",
    'description': """This odoo apps helps to print product image in sale and invoice report of odoo. user can see images in the sale order line as well as account invoice line. 
    
Sale invoice product image
Product image in so lines 
SO line product image
Sale order product image
Image on invoice 
Product image on invoice 
Product image on sale order line 
Image sale order line
Print product image
Print image on invoice
Sale order product image
Invoice product image 
Product image on sale order 




    """,
    "license" : "OPL-1",
    'depends': ['base','sale_management','account'],
    'data': [
            'report/report_for image.xml',
            'report/report_for_invoice_image.xml',
            'views/sale_order_line_image_views.xml',
            'views/invoice_image_views.xml',
            ],
    'installable': True,
    'auto_install': False,
    'price': 15,
    'currency': "EUR",
    'category': 'Sales',
    
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
