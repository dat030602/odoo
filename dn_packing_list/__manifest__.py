# -*- coding: utf-8 -*-
{
    'name': 'Packing List',
    'version': '19.0.0.3',
    'author': "Majorbird",
    "website": "https://www.majorbird.com",
    'category': 'Inventory',
    'summary': 'This module revolutionizes the way you manage your packing lists in Odoo. The module adds functionality to create, track, and manage packing lists with ease. With its comprehensive set of features, this module takes the guesswork out of packing list management, optimizing your logistics operations and ensuring no detail is overlooked.', 
    'depends': [
        'web',
        'sale',
        'sale_management',
        'sale_stock',
        'stock',
        'account',
    ],
    'data': [
        'security/packing_list_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/packing_list_stage_views.xml',
        'views/packing_list_views.xml',
        'views/packing_list_line_views.xml',
        'views/carton_type.xml',
        'views/shipping_destination.xml',
        'views/menu.xml',

        'wizard/add_to_packing_list_wizard_views.xml',
        'wizard/sale_make_invoice_advance_views.xml',

        'views/inherit_sale_order.xml',
        'views/inherit_account_move.xml',
        'views/inherit_product_template.xml',
        # Report
        'reports/paper_format.xml',
        'reports/report_packing_list.xml',
    ],
    '_documentation': {  
        'banner': 'banner.png',   
        'icon': 'icon.png',   
        'excerpt': 'The Packing List Management module enhances Logistics Management by providing robust and easy-to-use tools to manage packing items.',  
        'summary': 'The Packing List Management module developed by MajorBird, Inc., revolutionizes the way you manage your packing lists in Odoo. The module adds functionality to create, track, and manage packing lists with ease. With dependencies on sales and human resources modules, it fits seamlessly into your existing Odoo ecosystem. The module offers out-of-the-box support for a range of functionalities including packing list stages, carton types, shipping destinations, and sale order and account move inheritances among others. With its comprehensive set of features, this module takes the guesswork out of packing list management, optimizing your logistics operations and ensuring no detail is overlooked.',  
        'issue': 'Managing packing list information can be a complex task that requires a lot of manual administration and tracking.',  
        'solution': 'The Packing List Management module simplifies this process by providing a comprehensive suite of tools integrated directly within the Odoo platform.',  
        'manual': [     
            {  
            'title': 'Installation and Setup',  
            'description': 'Begin by installing the module from the Odoo Apps store. Complete the setup by following the on-screen guide.',  
            'images': ['image1.png']  
            },
            {  
            'title': 'Configuring for Carton',  
            'description': "Navigate to 'Sales' > 'Configuration' > 'Carton Type' then Create and configure for carton.",  
            'images': ['image2_1.png','image2_2.png']  
            },
            {  
            'title': 'Configuring for Packing List Stage',  
            'description': "Navigate to 'Sales' > 'Configuration' > 'Packing List Stage', we can design and create a new stage for the Packing List.",  
            'images': ['image3_1.png','image3_2.png']  
            },
            {  
            'title': 'Packing List Line Report',  
            'description': "Navigate to 'Sales' > 'Configuration' > 'Packing List Line'. Here will store all the report for the Packing List Line",  
            'images': ['image4.png']  
            },
            {  
            'title': 'Create a Packing List',  
            'description': "After create a SO, we can see the 'Packing List' button(1). When click the button (1), it will raise the Packing List wizard to ensure which data we use to create the Packing List. The purpose of the 'Packing List' button (2) is to showing all related packing list to the current SO.",  
            'images': ['image5_1.png','image5_2.png']  
            },
            {  
            'title': 'Configuring for Packing List',  
            'description': "After confirm the SO to create the Packing List, the Packing List will default at stage 'New'.",  
            'images': ['image6.png']  
            },
            {  
            'title': 'Confirm to create the Delivery',  
            'description': "When stage at 'Review', user can create a Delivery order when click on 'Deliver' button. Make sure the Packing List has the delivery address before confirm delivery. When everything is done, it will create a Delivery Order and change the stage to 'Deliverd'",  
            'images': ['image7_1.png','image7_2.png','image7_3.png','image7_4.png']  
            },
            {  
            'title': 'Confirm to create the Invoice',  
            'description': "When stage at 'Delivered', user can create a Invoice order when click on 'Invoice' button. When everything is done, it will create a Invoice and change the stage to 'Invoiced'",  
            'images': ['image8_1.png','image8_2.png']  
            },
        ],  
        'features': [  
            {  
            'title': 'Carton Type Management',  
            'description': 'Manage different types of cartons used in packing.',  
            },  
            {  
            'title': 'Shipping Destination Management',  
            'description': 'Keep track of various shipping destinations.',  
            },  
        ],  
    },
    'assets': {
        'web.assets_backend': [
            'dn_packing_list/static/src/css/custom_style.css',
        ],
    },
    'images': ['static/description/banner_slide.gif'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
}