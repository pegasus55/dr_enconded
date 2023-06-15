# -*- coding: utf-8 -*-
{
    'name': "Contacts",
    'version': '14.0.1.0.0',
    'summary': """
        Module to manage contacts.
        """,
    'description': """
        Module to manage contacts. It incorporates filters, the concept of a region for a province and the concept of a parish.
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
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'contacts',
            'base_geolocalize'
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        'views/res_country_state_view.xml',
        'views/res_city_view.xml',
        'views/res_parish_view.xml',
        'views/res_partner_view.xml',
    ],
    'demo': [],
    # 'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}