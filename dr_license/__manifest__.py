# -*- coding: utf-8 -*-
{
    'name': "Licenses",
    'version': '1.0',
    'summary': """Module to manage licenses contracted by clients.
    """,
    'description': """Module to manage licenses contracted by clients.
    """,
    'category': 'Uncategorized',
    'author': "Dainovy Rodríguez Marrero",
    'company': 'Dainovy Rodríguez Marrero',
    'maintainer': 'Dainovy Rodríguez Marrero',
    'website': "https://www.nukleosolutions.com",
    'support': 'drodriguez@nukleosolutions.com',
    'price': 0.0,
    'currency': 'USD',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail'],

    # always loaded
    'data': [
        'security/category.xml',
        'security/group.xml',
        'security/ir.model.access.csv',

        'data/normative.xml',
        'data/device_brand.xml',
        'data/device_brand_model.xml',
        'data/salable_module.xml',
        'data/cron_data.xml',
        'data/parameter.xml',

        'views/dr_licence_views.xml',
        'views/dr_licence_menu.xml',
        'views/dr_templates_email_notifications.xml',
        'views/res_config_settings.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
