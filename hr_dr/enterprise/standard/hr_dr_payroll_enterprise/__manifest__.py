# -*- coding: utf-8 -*-
{
    'name': "Payroll for odoo enterprise",
    'version': '16.0.1.0.0',
    'summary': """
        Module to manage the payroll of collaborators in odoo enterprise.
    """,
    'description': """
        Module to manage the payroll of collaborators in odoo enterprise.
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
            'hr_payroll',
            'hr_payroll_account',
            'account',
            'account_accountant',
            'account_batch_payment',
        ],

    # always loaded
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',

        'data/hr_salary_rule_category_inactive.xml',
        'data/hr_salary_rule_category.xml',
        'data/hr_payroll_structure_inactive.xml',
        'data/hr_payslip_input_type_inactive.xml',
        'data/hr_payslip_input_type.xml',

        'wizard/register_account_payment.xml',
        'wizard/register_res_payment.xml',
        'wizard/register_red13_payment.xml',
        'wizard/register_red14_payment.xml',

        'views/res_company.xml',
        'views/hr_payslip_input_type.xml',
        'views/hr_input.xml',
        'views/hr_salary_rule_category.xml',
        'views/hr_payslip_views.xml',
        'views/hr_contract.xml',
        'views/hr_pay_living_wage.xml',
        'views/hr_tenths.xml',
        'views/hr_payment_utility.xml',
        'views/retired_employees.xml',
        'views/account_payment.xml',
        'views/account_batch_payment.xml',
        'views/hr_personal_expense.xml',
        'views/res_config_settings.xml',

        'wizard/generate_hr_fortnight.xml',

        'views/hr_dr_payroll_enterprise_menu.xml',


        # 'views/hr_salary_rule.xml',
        # 'views/hr_payroll_structure.xml',
        # 'views/hr_employee_information.xml',
        # 'views/hr_rent_tax_table.xml',
        # 'views/retired_employees.xml',
        # 'views/hr_payment_utility.xml',
        # 'views/hr_tenths.xml',
        #
        # 'views/hr_assets_liquidation_view.xml',
        #
        # 'views/retired_employees_email_notifications.xml',




    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    # 'post_init_hook': '_archive_salary_rules',
}
