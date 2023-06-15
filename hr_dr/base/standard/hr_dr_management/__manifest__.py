# -*- coding: utf-8 -*-
{
    'name': "Management",
    'version': '16.0.1.0.0',
    'summary': """
        Module to manage the general configurations of human talent.
    """,
    'description': """
        Module to manage the general configurations of human talent.
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
            'hr',
        ],
    'data': [
        'security/category.xml',
        'security/group.xml',
        'security/ir.model.access.csv',

        'views/res_config_settings.xml',
        'views/hr_dr_view.xml',
        'views/hr_salary_rule_process.xml',
        'views/hr_dr_menu.xml',

        'views/hr_dr_templates_email_notifications.xml',
        'views/hr_dr_page_notifications.xml',

        'wizard/hr_dr_wizard_reassign_notifications.xml',
        'wizard/hr_dr_wizard_generate_scheme_notifications.xml',

        'data/hour_extra.xml',
        'data/hour_night.xml',
        'data/hr_salary_rule_process.xml',
        'data/tz.xml',
        'data/parameter.xml',
        'data/cron_data.xml',

    ],
    'demo': [
    ],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_assign_group_to_default_user_template',
}