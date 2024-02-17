# -*- coding: utf-8 -*-
{
    'name': "Collaborators",
    'version': '1.0',
    'summary': """        
        Module to manage the information of the collaborators.""",
    'description': """
        Module to manage the information of the collaborators.
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
            'hr',

            'l10n_latam_base',
            'l10n_ec',

            'dr_start_system',

            'hr_dr_management',
            'dr_contacts_ec',
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        'wizard/hr_update_department_employee.xml',
        'wizard/hr_transfer_employee.xml',
        'wizard/hr_departure_wizard_views.xml',
        'wizard/hr_reentry_employee.xml',

        'views/hr_employee.xml',
        'views/hr_employee_public.xml',
        'views/hr_job.xml',
        'views/hr_position.xml',
        'views/hr_position_function.xml',
        'views/hr_profession.xml',
        'views/hr_departure_reason_views.xml',
        'views/hr_employee_department_history.xml',
        'views/hr_employee_company_history.xml',
        'views/hr_employee_backup.xml',
        'views/hr_judicial_withholding.xml',
        'views/hr_employee_family_load.xml',
        'views/hr_catastrophic_disease.xml',
        'views/hr_employee_allergies.xml',
        'views/hr_employee_food_preferences.xml',
        'views/res_partner_view.xml',

        'views/res_config_settings.xml',
        'views/mail_template.xml',
        'views/menu.xml',

        'data/department.xml',
        'data/catastrophic_disease.xml',
        'data/parameter.xml',
        'data/employee_admin.xml',
        'data/decimal_precision.xml',
        'data/departure_reason.xml',
        'data/resource_data.xml',
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