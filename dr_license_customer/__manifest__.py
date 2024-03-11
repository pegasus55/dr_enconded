# -*- coding: utf-8 -*-
{
    'name': "License customer",

    'version': '1.1',
    'summary': """Module to activate the license on clients.
        """,
    'description': """Module to activate the license on clients.
        """,
    'category': 'Uncategorized',
    'author': "Dainovy Rodríguez Marrero",
    'company': 'Dainovy Rodríguez Marrero',
    'maintainer': 'Dainovy Rodríguez Marrero',
    'website': "https://www.nukleosolutions.com",
    'support': 'drodriguez@nukleosolutions.com',
    'price': 0.0,
    'currency': 'USD',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list


    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'mail',
            'web',
        ],

    # always loaded
    'data': [
        'security/category.xml',
        'security/group.xml',
        'security/ir.model.access.csv',

        'wizard/request_license.xml',

        'data/parameter.xml',
        'views/views.xml',
        'views/res_config_settings.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
        'web.assets_backend': [
            'dr_license_customer/static/src/css/widget.css',
            'dr_license_customer/static/src/js/device_list.js',
            'dr_license_customer/static/src/js/app_list.js',
            'dr_license_customer/static/src/xml/device_list.xml',
            'dr_license_customer/static/src/xml/app_list.xml',
        ],
    },
    'external_dependencies': {'python': ['cryptography']}
}
