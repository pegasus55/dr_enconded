# -*- coding: utf-8 -*-
{
    'name': "Payroll for odoo community",
    'version': '1.0',
    'summary': """
        Module to manage the payroll of collaborators in odoo community.
    """,
    'description': """
        Module to manage the payroll of collaborators in odoo community.
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
            'dr_start_system',
            'hr_dr_management',
            'hr_dr_employee',
            'hr_dr_payroll_base',
            'om_hr_payroll',
            'om_hr_payroll_account',
            'om_account_accountant'
        ],

    # always loaded
    'data': [
        'security/category.xml',
        'security/group.xml',
        'security/ir.model.access.csv',

        'data/hr_salary_rule_category_inactive.xml',
        'data/hr_salary_rule_inactive.xml',
        'data/hr_payroll_structure_inactive.xml',
        'data/hr_salary_rule_category.xml',
        'data/hr_contribution_register.xml',

        'views/res_config_settings.xml',
        'views/hr_contract.xml',
        'views/hr_dr_payroll_community_menu.xml',
        'views/hr_salary_rule_category.xml',
        'views/hr_salary_rule.xml',
        'views/hr_payroll_structure.xml',
        'views/hr_department.xml',
        'views/hr_payslip.xml',

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
