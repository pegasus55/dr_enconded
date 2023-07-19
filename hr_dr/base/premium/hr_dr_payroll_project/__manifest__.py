# -*- coding: utf-8 -*-
{
    'name': "Payroll project analytics",

    'summary': """
        Associates project analytic account lines with collaborator payslips.""",

    'description': """
        Associates project analytic account lines with collaborator payslips.
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
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'version': '16.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'project_enterprise',
            'timesheet_grid',
            'hr_payroll_account'
        ],

    # always loaded
    'data': [
        'views/res_config_settings.xml',
    ],
    'license': 'AGPL-3',
}
