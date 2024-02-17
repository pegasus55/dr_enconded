# -*- coding: utf-8 -*-
{
    'name': "Departments",
    'version': '1.0',
    'summary': """
        Module to manage the departments of the company.
    """,
    'description': """
        Module to manage the departments of the company.
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
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'hr',
            'dr_start_system',
        ],

    # always loaded
    'data': [
        'views/hr_dr_menu_view.xml',
        'views/hr_dr_department_view.xml',
        'views/res_config_settings.xml',

        'data/department.xml'
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