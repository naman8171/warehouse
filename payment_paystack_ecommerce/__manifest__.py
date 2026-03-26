# -*- coding: utf-8 -*-
{
    'name': "Paystack Payment Acquirer",
    'category': 'Accounting/Payment Acquirers',
    'sequence': -100,
    'summary': 'Payment Acquirer: Custom Paystack Implementation',
    'author': 'Samuel Akoh <ojima.asm@gmail.com>',
    'description': """Custom Paystack Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/payment_views.xml',
        'views/payment_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'images': ['static/description/icon.png'],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'assets': {
        'web.assets_frontend': [
            'payment_paystack_ecommerce/static/src/js/payment_form.js',
        ],
    },
    'license': 'LGPL-3',

}
