# -*- coding: utf-8 -*-
{
    # TODO Cargar los metodos de pago.
    # TODO Cargar las lineas de los metos de pago.
    'name': "Ecuadorian location",
    'version': '1.0',
    'summary': """
        Ecuadorian location.""",
    'description': """
        Ecuadorian location.
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
            'l10n_ec'
        ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',

        'views/res_company.xml',
        'views/res_partner_bank.xml',
        'views/account_payment.xml',

        # 'data/account_payment_method.xml',
        # 'data/account_payment_method_line.xml',
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
