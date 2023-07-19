# -*- coding: utf-8 -*-
{
    'name': 'Collaborators credit',
    'version': '16.0.1.0.0',
    'summary': 'Module to manage the credits of the collaborators.',
    'description': """
        Module to manage the credits of the collaborators.
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
            'account',
            'hr_dr_employee',
            'hr_dr_payroll',
        ],
    'data': [
        'security/category.xml',
        'security/group.xml',
        'security/ir.model.access.csv',

        'views/hr_credit_seq.xml',
        'views/hr_credit.xml',
        #'views/hr_payroll.xml',
        'views/hr_dr_menu_view.xml',
        'views/res_config_settings.xml',
        'views/hr_dr_templates_email_notifications.xml',

        'data/parameter.xml',
        #'data/salary_rule_credit.xml',
        'data/decimal_precision.xml',
        'data/cron_job.xml',

        'report/employee_credit_request.xml',

    ],
    'demo': [],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_assign_group_to_default_user_template',
}
