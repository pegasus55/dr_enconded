# -*- coding: utf-8 -*-
{
    'name': "Schedules",
    'version': '16.0.1.0.0',
    'summary': """
        Module to manage the schedules of the collaborators.
        """,
    'description': """
        Module to manage the schedules of the collaborators.
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

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'dr_base',
            'dr_start_system',
            'hr_dr_management',
            'hr_dr_employee',
            'to_attendance_device',
            'report_xlsx',
        ],

    # always loaded
    'data': [
        'security/category.xml',
        'security/group.xml',
        'security/ir.model.access.csv',

        'wizard/import_employee_hour_extra_approval_request.xml',

        'views/hr_dr_schedule_view.xml',
        'views/res_config_settings.xml',
        'views/hr_dr_templates_email_notifications.xml',

        'views/hr_dr_menu_view.xml',

        'wizard/assign_schedule.xml',
        'wizard/delete_employee_shift.xml',
        'wizard/import_user_attendance.xml',
        'wizard/correct_user_attendance_state.xml',
        'wizard/export_employee_hour_extra.xml',
        'wizard/import_employee_hour_extra.xml',
        'wizard/compute_attendance.xml',
        'wizard/compute_summary.xml',
        'wizard/export_period_summary.xml',

        'data/nomenclature_schedule.xml',
        'data/decimal_precision.xml',
        'data/cron_data.xml',
        'data/resource_data.xml',
        'data/attendance_state_data.xml',
        'data/attendance_device.xml',
        'data/parameter.xml',

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
    'post_init_hook': '_assign_group_to_default_user_template',
}