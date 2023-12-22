# -*- coding: utf-8 -*-
{
    'name': "Skills",
    'version': '1.0',
    'summary': """
        Module to manage the skills of the collaborators.""",
    'description': """
        Module to manage the skills of the collaborators.
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

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'dr_start_system',
            'hr_skills',
            'hr_dr_employee'
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',


        'data/hr_skill_category.xml',
        'data/hr_skill_type.xml',
        'data/hr_skill_level.xml',
        'data/hr_skill.xml',


    ],
    # only loaded in demonstration mode
    'demo': [
        #'demo/demo.xml',
    ],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
