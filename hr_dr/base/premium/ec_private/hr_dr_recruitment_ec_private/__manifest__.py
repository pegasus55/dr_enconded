# -*- coding: utf-8 -*-
{
    'name': "Recruitment (EC Private)",

    'summary': """
        Module to manage the collaborators recruitment process.""",

    'description': """
        Module to manage the collaborators recruitment process. It incorporates the information for the private sector of Ecuador.
    """,

    'category': 'Human Resources',
    'author': "Dainovy Rodríguez Marrero",
    'company': 'Dainovy Rodríguez Marrero',
    'maintainer': 'Dainovy Rodríguez Marrero',
    'website': "https://www.nukleosolutions.com",
    'support': 'drodriguez@nukleosolutions.com',
    'price': 0.0,
    'currency': 'USD',
    'version': '16.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'dr_start_system',
            'hr_dr_recruitment',
            'hr_dr_management_ec_private'
        ],

    # always loaded
    'data': [
        'data/normative_nomenclature.xml',
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
