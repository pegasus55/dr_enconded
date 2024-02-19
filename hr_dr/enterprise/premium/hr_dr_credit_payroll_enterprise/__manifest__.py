# -*- coding: utf-8 -*-
{
    'name': "Collaborators credit payroll",
    'version': '1.0.0',
    'summary': """
    """,

    'description': """
    """,

    'category': 'Generic Modules/Human Resources',
    'author': "Dainovy Rodriguez Marrero",
    'company': 'Dainovy Rodriguez Marrero',
    'maintainer': 'Dainovy Rodriguez Marrero',
    'website': "https://www.nukleosolutions.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'hr_dr_credit',
            'hr_dr_payroll_enterprise',
            'hr_dr_payroll_enterprise_ec_private'
        ],

    # always loaded
    'data': [
        'data/salary_rule_credit.xml',

        'views/hr_input.xml',
        'views/hr_credit.xml',
        'views/hr_credit_line.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}