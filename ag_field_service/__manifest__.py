# -*- coding: utf-8 -*-

{
    "name" : "Field Service",
    "version" : "14.0.0.0",
    'category' : "Customization",
    "summary" : "Field Service",
    "description": """
                 Field Service customization
    """,
    "author" : "Arpit Goel",
    "website" : "",
    "depends" : ['hr', 'stock', 'account', 'purchase', 'purchase_requisition', 'industry_fsm', 'project_enterprise', 'helpdesk', 'helpdesk_fsm', 'account_followup', 'ag_multi_branch'],
    "data" :[
        'security/fs_security.xml',
        'security/ir.model.access.csv',
        'data/mail_data.xml',
        'data/ir_sequence.xml',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/res_branch_views.xml',
        'views/job_order_views.xml',
        'views/cost_entry_views.xml',
        'views/common_area_cost_views.xml',
        'views/power_cost_views.xml',
        'views/flat_type_views.xml',
        'views/scope_work_views.xml',
        'views/helpdesk_views.xml',
        'views/project_task_views.xml',
        'views/equipment_views.xml',
        'views/stock_picking_views.xml',
        'views/purchase_views.xml',
        'views/payment_views.xml',
        'reports/report_paperformat.xml',
        'reports/report_rfq.xml',
        'reports/report_purchase_order.xml',
        'wizard/vendor_bill_reapproval_views.xml',
        'views/account_move_views.xml',
        'wizard/create_task_views.xml',
    ],
    "auto_install": False,
    "installable": True,
    'license': 'LGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
