# -*- coding: utf-8 -*-
{
    'name': 'Collaborators loan accounting',
    'version': '1.0.0',
    'summary': 'Accounting entries for collaborators loans.',
    'description': """
        Module to incorporate the accounting entries to the loans of the collaborators.
        """,
    'category': 'Generic Modules/Human Resources',
    'author': "Dainovy Rodriguez Marrero",
    'company': 'Dainovy Rodriguez Marrero',
    'maintainer': 'Dainovy Rodriguez Marrero',
    'website': "https://www.drm.com",
    'depends': [
        'base', 'dr_start_system', 'hr_payroll', 'hr', 'account', 'hr_dr_loan',
    ],
    'data': [
        'views/hr_loan_acc.xml',
        'views/res_config_settings.xml',

        'data/parameter.xml',

    ],
    'demo': [],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
