# -*- coding: utf-8 -*-

{
    "name" : "Approval Customization ISN",
    "version" : "14.0.0.0",
    'category' : "Customization",
    "summary" : "Approval Customization",
    "description": """
                 Approval Customization for ISN
    """,
    "author" : "ISN",
    "website" : "",
    "depends" : ['base','mail','hr','account','approvals', 'ag_multi_branch'],
    "data" :[
        'security/ir.model.access.csv',
        'data/mail_data.xml',
        'wizard/payment_approval_entry_views.xml',
        'wizard/approval_request_reapproval_views.xml',
        'views/hr_department_view.xml',
        'views/approval_request_views.xml',
        'views/approval_category_views.xml',
        'views/account_move_view.xml',
        'views/region_location_views.xml',
        'views/product_views.xml',
        'views/purchase_views.xml',
        'views/picking_views.xml',
        'views/stock_warehouse_views.xml',
    ],
    'qweb': [
    ],
    "auto_install": False,
    "installable": True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
