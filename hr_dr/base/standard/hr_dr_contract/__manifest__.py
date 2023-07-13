# -*- coding: utf-8 -*-
{
    'name': "Contracts",
    'summary': """
        Module to manage the contract information of the collaborators.
    """,
    'description': """
        Module to manage the contract information of the collaborators.
    """,
    'category': 'Human Resources',
    'author': "Dainovy Rodríguez Marrero",
    'company': 'Dainovy Rodríguez Marrero',
    'maintainer': 'Dainovy Rodríguez Marrero',
    'website': "https://www.nukleosolutions.com",
    'support': 'drodriguez@nukleosolutions.com',
    'price': 0.0,
    'currency': 'USD',
    'depends':
        [
            'base',
            'dr_start_system',
            'hr_contract',
            'hr_dr_management'
        ],
    'data': [
        'security/ir.model.access.csv',

        'views/hr_contract_type.xml',
        'views/hr_payroll_structure_type.xml',
        'views/hr_contract.xml',
        'views/res_config_settings.xml',
        'views/mail_template.xml',
        'views/menu.xml',

        'data/hr_payroll_structure_type.xml',
        'data/cron_data.xml',
        'data/parameter.xml',
        'data/decimal_precision.xml',
    ],
    'demo': [
    ],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}