# -*- coding: utf-8 -*-
{
    'name': "Payroll base",
    'version': '1.0',
    'summary': """
        Module to manage the payroll of collaborators.
    """,
    'description': """
        Module to manage the payroll of collaborators.
    """,
    'category': 'Human Resources',
    'author': "Dainovy Rodríguez Marrero",
    'company': 'Dainovy Rodríguez Marrero',
    'maintainer': 'Dainovy Rodríguez Marrero',
    'website': "https://www.nukleosolutions.com",
    'support': 'drodriguez@nukleosolutions.com',
    'price': 0.0,
    'currency': 'USD',

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'contacts',
            'dr_start_system',
            'hr_dr_management',
            'hr_dr_employee',
            'hr_dr_contract',
        ],

    # always loaded
    'data': [
        'data/decimal_precision.xml',
        'data/parameter.xml',
        # 'data/res_partner.xml',
        'data/hr_contribution_register.xml',
        'data/hr_basic_family_basket.xml',

        'wizard/import_utility_external_service.xml',
        'wizard/import_input.xml',
        'wizard/clone_salary_rule.xml',

        'views/hr_sbu.xml',
        'views/hr_living_wage.xml',
        'views/schedule_legal_obligations.xml',
        'views/retired_employees.xml',
        'views/hr_payment_utility.xml',
        'views/res_partner.xml',
        'views/hr_tenths.xml',
        'views/hr_pay_living_wage.xml',
        'views/hr_dr_templates_email_notifications.xml',
        'views/hr_historical_provision.xml',
        'views/hr_input.xml',
        'views/hr_fortnight.xml',
        'views/hr_contribution_register.xml',
        'views/hr_basic_family_basket.xml',
        'views/base_file_report_view.xml',

        'wizard/generate_hr_fortnight.xml',

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
