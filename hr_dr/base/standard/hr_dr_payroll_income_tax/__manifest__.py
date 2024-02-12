# -*- coding: utf-8 -*-
{
    'name': "Payroll income tax",
    'version': '1.0',
    'summary': """
    Module to incorporate the calculation of income tax.
    """,

    'description': """
        Module to incorporate the calculation of income tax to the payroll for the Ecuadorian location.
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

    # any module necessary for this one to work correctly
    'depends':
        [
            'base',
            'hr_dr_payroll_base'
        ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',

        'data/bfb_per_fl.xml',
        'data/hr_personal_expenses_category.xml',

        'views/bfb_per_fl.xml',
        'views/hr_personal_expenses_category.xml',
        'views/hr_personal_expense.xml',
        'views/hr_rent_tax_table.xml',

        'wizard/generate_rdep.xml',


    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}