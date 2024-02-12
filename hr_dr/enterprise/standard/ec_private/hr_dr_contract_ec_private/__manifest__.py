# -*- coding: utf-8 -*-
{
    'name': "Contracts (EC Private)",
    'summary': """
        Module to manage the contract information of the collaborators.
    """,
    'description': """
        Module to manage the contract information of the collaborators. It incorporates the information for the private sector of Ecuador.
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
            'hr_dr_management_ec_private',
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        'data/hr_contract_type.xml',

        'views/menu.xml',

        'views/hr_occupational_structure_level_view.xml',
        'views/hr_occupational_structure_view.xml',
        'views/hr_sector_commission_view.xml',
        'views/hr_branch_economic_activity_view.xml',
        'views/hr_subbranch_economic_activity.xml',
        'views/hr_sector_table_view.xml',
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
