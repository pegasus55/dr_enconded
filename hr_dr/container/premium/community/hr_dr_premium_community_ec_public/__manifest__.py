# -*- coding: utf-8 -*-
{
    'name': "Human talent premium community (EC Public)",

    'summary': """
        Premium version of the community human talent system for the public sector of Ecuador.""",

    'description': """
        Premium version of the community human talent system for the public sector of Ecuador.
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
            'hr_dr_standard_ec_public',
            'hr_dr_skills',
            'hr_dr_employee_certificates',
            'hr_dr_employee_notifications',
            'hr_dr_department_additional_manager',
            'contacts_maps',
            'bi_employee_age',
            'hr_organizational_chart',
            'password_security',
            'auth_password_policy',
            'oh_employee_documents_expiry',
        ],

    # always loaded
    'data': [
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
