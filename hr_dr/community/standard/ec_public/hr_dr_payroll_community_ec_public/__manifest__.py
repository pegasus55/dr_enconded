# -*- coding: utf-8 -*-
{
    'name': "Payroll for odoo community (EC Public)",
    'version': '16.0.1.0.0',
    'summary': """
        Module to manage the payroll of collaborators.
    """,
    'description': """
        Module to manage the payroll of collaborators. It incorporates the information for the public sector of Ecuador.
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
            'hr_dr_payroll_community'
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
    'application': False,
}
