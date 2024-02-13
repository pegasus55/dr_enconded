# -*- coding: utf-8 -*-

{
    'name': 'Collaborators loan',
    'version': '1.0',
    'summary': 'Module to manage collaborators loans.',
    'description': """
        Module to manage collaborators loans.
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
            'hr_dr_employee',
        ],
    'data': [
        'security/category.xml',
        'security/group.xml',
        'security/ir.model.access.csv',

        'views/hr_loan_seq.xml',
        'views/hr_loan.xml',
        'views/hr_loan_line.xml',
        'views/hr_employee.xml',
        'views/hr_dr_menu_view.xml',
        'views/res_config_settings.xml',
        'views/hr_dr_templates_email_notifications.xml',

        'data/parameter.xml',
        'data/decimal_precision.xml',

        'report/loan_request.xml',

    ],
    'demo': [],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_assign_group_to_default_user_template',
}
