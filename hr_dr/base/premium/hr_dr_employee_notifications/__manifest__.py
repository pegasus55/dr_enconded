# -*- coding: utf-8 -*-
{
    'name': "Collaborators notifications",
    'version': '1.0',
    'summary': """
        Module to send notifications.""",
    'description': """
        Module to send birthday notifications, anniversary notifications, personal income notifications, personal exit notifications, profession celebration date.
    """,
    'category': 'Human Resources',
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
            'dr_start_system',
            'hr_dr_employee'
        ],

    # always loaded
    'data': [
        'data/parameter.xml',
        'data/cron_data.xml',

        'views/res_config_settings.xml',
        'views/hr_dr_employee_view.xml',
        'views/hr_profession_view.xml',
        'views/hr_dr_templates_email_notifications.xml',
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
