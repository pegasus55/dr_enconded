# -*- coding: utf-8 -*-
{
    'name': "Account batch payment enterprise for ecuadorian location",
    'version': '1.0',
    'summary': """
        Account batch payment enterprise for ecuadorian location.""",
    'description': """
        Account batch payment enterprise for ecuadorian location.
    """,

    'author': "Dainovy Rodríguez Marrero",
    'company': 'Dainovy Rodríguez Marrero',
    'maintainer': 'Dainovy Rodríguez Marrero',
    'website': "https://www.nukleosolutions.com",
    'support': 'drodriguez@nukleosolutions.com',
    'price': 0.0,
    'currency': 'USD',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Localization',

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'account_batch_payment'
        ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',

        'views/account_batch_payment.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
