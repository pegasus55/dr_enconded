# -*- coding: utf-8 -*-
{
    'name': "Contacts EC",
    'version': '14.0.1.0.0',
    'summary': """
        Module to manage contacts.
        """,
    'description': """
        Module to manage contacts. Incorporates the data for Ecuador.
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
            'dr_contacts'
        ],

    # always loaded
    'data': [
        'data/res.country.state.csv',
        'data/res.city.csv',
        'data/res.parish.csv'
    ],
    'demo': [],
    # 'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}