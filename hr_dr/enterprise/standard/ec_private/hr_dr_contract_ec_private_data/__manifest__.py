# -*- coding: utf-8 -*-
{
    'name': "Contracts (EC Private Data)",
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
            'hr_dr_contract_ec_private',
        ],

    # always loaded
    'data': [

        'data/hr.occupational.structure.level.csv',
        'data/hr.occupational.structure.csv',
        'data/hr.sector.commission.csv',
        'data/hr.branch.economic.activity.csv',
        'data/hr.subbranch.economic.activity.csv',
        'data/hr.sector.table.csv',
        'data/hr.sector.table.year.csv',
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
