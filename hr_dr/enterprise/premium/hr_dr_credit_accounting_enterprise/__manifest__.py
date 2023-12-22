# -*- coding: utf-8 -*-
{
    'name': 'Collaborators credit accounting',
    'version': '1.0.0',
    'summary': 'Accounting entries for collaborators credit.',
    'description': """
        Module to incorporate the accounting entries to the credits of the collaborators.
        """,
    'category': 'Generic Modules/Human Resources',
    'author': "Dainovy Rodriguez Marrero",
    'company': 'Dainovy Rodriguez Marrero',
    'maintainer': 'Dainovy Rodriguez Marrero',
    'website': "https://www.nukleosolutions.com",
    'depends':
        [
            'base',
            'dr_start_system',
            'hr_payroll',
            'hr',
            'account',
            'hr_dr_credit',
        ],
    'data': [
        'views/hr_credit.xml',
        'views/res_company.xml',
    ],
    'demo': [],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}