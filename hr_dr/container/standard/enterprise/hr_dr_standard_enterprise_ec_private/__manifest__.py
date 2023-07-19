# -*- coding: utf-8 -*-
{
    'name': "Human talent standard enterprise (EC Private)",

    'summary': """
        Standard version of the enterprise human talent system for the private sector of Ecuador.""",

    'description': """
        Standard version of the enterprise human talent system for the private sector of Ecuador.
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
    'version': '16.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'dr_start_system',

            'hr_dr_management',
            'hr_dr_management_ec_private',

            'hr_dr_employee',

            'hr_dr_contract',
            'hr_dr_contract_ec_private',
            'hr_dr_contract_ec_private_data',

            'hr_dr_payroll_base',
            'hr_dr_payroll_enterprise',
            'hr_dr_payroll_enterprise_ec_private',
        ],

    # always loaded
    'data': [
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
