{
    'name': 'Inventory Zeroization',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Cascading stock zeroization by merchant/owner',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/zeroization_wizard_views.xml',
        'views/zeroization_log_views.xml',
        'views/effective_date_wizard_views.xml',
        'views/stock_quant_view.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
}