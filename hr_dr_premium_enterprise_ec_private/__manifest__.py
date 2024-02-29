# -*- coding: utf-8 -*-
{
    'name': "Human talent premium enterprise (EC Private)",

    'summary': """
        Premium version of the enterprise human talent system for the private sector of Ecuador.""",

    'description': """
        Premium version of the enterprise human talent system for the private sector of Ecuador.
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

            'hr_dr_standard_enterprise_ec_private',

            'hr_dr_credit',
            'hr_dr_department',
            'hr_dr_department_additional_manager',
            'hr_dr_employee_certificates',
            'hr_dr_employee_notifications',
            'hr_dr_loan',
            'hr_dr_permissions',
            'hr_dr_recruitment',
            'hr_dr_schedule',
            'hr_dr_skills',
            'hr_dr_vacations',

            'hr_dr_permissions_ec_private',
            'hr_dr_recruitment_ec_private',
            'hr_dr_schedule_ec_private',
            'hr_dr_vacations_ec_private',

            'hr_dr_appraisal_enterprise',
            'hr_dr_credit_accounting_enterprise',
            'hr_dr_credit_payroll_enterprise',
            'hr_dr_loan_accounting_enterprise',
            'hr_dr_loan_payroll_enterprise',
            'hr_dr_payroll_enterprise_holidays',
            'hr_dr_payroll_enterprise_vacations',

            'hr_dr_payroll_enterprise_holidays_ec_private',
            'hr_dr_payroll_enterprise_vacations_ec_private',
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
