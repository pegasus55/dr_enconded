# -*- coding: utf-8 -*-
{
    'name': "Collaborators appraisal for odoo community",
    'summary': """
        Module to manage collaborators appraisal in odoo community.""",

    'description': """
        Module to manage collaborators appraisal in odoo community.
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
    'depends':
        [
            'base',
            'dr_start_system',
            'hr',
            'survey',
            'web_timeline',
            'oh_appraisal'
        ],
    'data': [
    ],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}