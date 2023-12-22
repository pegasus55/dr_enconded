# -*- coding: utf-8 -*-
{
    'name': "Schedules (EC Public)",

    'summary': """
        Module to manage the schedules of the collaborators.""",

    'description': """
        Module to manage the schedules of the collaborators. It incorporates the information for the public sector of Ecuador.
    """,

    'category': 'Human Resources',
    'author': "Dainovy Rodríguez Marrero",
    'company': 'Dainovy Rodríguez Marrero',
    'maintainer': 'Dainovy Rodríguez Marrero',
    'website': "https://www.nukleosolutions.com",
    'support': 'drodriguez@nukleosolutions.com',
    'price': 0.0,
    'currency': 'USD',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'dr_start_system',
            'hr_dr_schedule',
            'hr_dr_management_ec_public'
        ],

    # always loaded
    'data': [
        'data/normative_nomenclature.xml',
        'data/normative_nomenclature_hour_extra.xml',
        'data/normative_nomenclature_hour_night.xml',
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
