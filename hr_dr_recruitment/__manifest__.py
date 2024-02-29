# -*- coding: utf-8 -*-
{
    'name': "Recruitment",
    'version': '1.0',
    'summary': """
        Module to manage the collaborators recruitment process.""",
    'description': """
        Module to manage the collaborators recruitment process.
    """,
    'category': 'Human Resources',
    'author': "Dainovy Rodríguez Marrero",
    'company': 'Dainovy Rodríguez Marrero',
    'maintainer': 'Dainovy Rodríguez Marrero',
    'website': "https://www.nukleosolutions.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'dr_start_system',
            'hr_recruitment',
            'mail',
            'hr_dr_employee',
            'web',
            'website_hr_recruitment',
            'hr_recruitment_survey',
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'security/hr_dr_recruitment_security.xml',

        'views/res_config_settings.xml',
        'views/hr_dr_recruitment_view.xml',
        'views/hr_dr_menu_view.xml',
        'views/hr_dr_templates_email_notifications.xml',

        'wizard/generate_scheme_schedule_process_staff_requirement.xml',

        'data/sequence.xml',
        'data/parameter.xml',
        'data/nomenclature_recruitment.xml',
        'data/degree.xml',

        'report/schedule_process_staff_requirement.xml',
        'report/job_profile.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_assign_group_to_default_user_template',
}