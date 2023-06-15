# -*- coding: utf-8 -*-
{
    'name': "Permissions",

    'summary': """
        Module to manage the permissions, licenses and service commissions of the collaborators.""",

    'description': """
        Module to manage the permissions, licenses and service commissions of the collaborators.
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
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'version': '16.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'dr_start_system',
            'hr_dr_employee',
            'mail',
            'hr_dr_schedule'
        ],

    # always loaded
    'data': [
        'security/category.xml',
        'security/group.xml',
        'security/ir.model.access.csv',

        'views/res_config_settings.xml',
        'views/hr_dr_permission_view.xml',
        'views/hr_dr_menu_view.xml',
        'views/hr_dr_page_notifications.xml',
        'views/hr_dr_templates_email_notifications.xml',

        'data/nomenclature.xml',
        'data/permission_type.xml',
        'data/parameter.xml'
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