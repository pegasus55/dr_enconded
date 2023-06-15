# -*- coding: utf-8 -*-
{
    'name': "Collaborators certificates",
    'version': '16.0.1.0.0',
    'summary': """
        Module to generate the work certificates of the collaborators.""",
    'description': """
        Module to generate the work certificates of the collaborators.
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
            'hr_contract',
            'hr',
            'hr_dr_employee'
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        'views/hr_dr_employee_view.xml',
        'views/hr_dr_work_certificate_history_view.xml',
        'views/res_config_settings.xml',

        'data/parameter.xml',

        'report/work_certificate.xml',
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
