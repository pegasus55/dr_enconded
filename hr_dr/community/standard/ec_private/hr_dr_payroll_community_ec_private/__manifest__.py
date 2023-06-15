# -*- coding: utf-8 -*-
{
    'name': "Payroll for odoo community (EC Private)",
    'version': '16.0.1.0.0',
    'summary': """
        Module to manage the payroll of collaborators.
    """,
    'description': """
        Module to manage the payroll of collaborators. It incorporates the information for the private sector of Ecuador.
    """,
    'category': 'Human Resources',
    'author': "Dainovy Rodríguez Marrero",
    'company': 'Dainovy Rodríguez Marrero',
    'maintainer': 'Dainovy Rodríguez Marrero',
    'website': "https://www.nukleosolutions.com",
    'support': 'drodriguez@nukleosolutions.com',
    'price': 0.0,
    'currency': 'USD',

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'hr_dr_payroll_community',
            'hr_dr_management_ec_private',
            'hr_dr_contract_ec_private',
        ],

    # always loaded
    'data': [
        'data/schedule_legal_obligations.xml',
        'data/hr_salary_rule.xml',
        'data/hr_payroll_structure_type.xml',
        'data/hr_payroll_structure.xml',
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
