# -*- coding: utf-8 -*-
{
    'name': "Payroll income tax for odoo enterprise",
    'version': '1.0',
    'summary': """
        Module to incorporate the calculation of income tax for odoo enterprise.""",

    'description': """
        Module to incorporate the calculation of income tax to the payroll for odoo enterprise 
        to the Ecuadorian location.
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
            'hr_dr_payroll_enterprise',
            'hr_dr_payroll_income_tax'
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        'views/hr_personal_expense.xml',

        'views/menu.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
