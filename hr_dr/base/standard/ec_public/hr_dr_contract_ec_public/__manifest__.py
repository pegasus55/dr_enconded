# -*- coding: utf-8 -*-
{
    'name': "Contracts (EC Public)",
    'summary': """
        Module to manage the contract information of the collaborators.
    """,
    'description': """
        Module to manage the contract information of the collaborators. It incorporates the information for the public sector of Ecuador.
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
            'hr_dr_contract',
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        'views/menu.xml',

        'views/hr_remuneration_scale.xml',
        'views/hr_contract.xml',
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
