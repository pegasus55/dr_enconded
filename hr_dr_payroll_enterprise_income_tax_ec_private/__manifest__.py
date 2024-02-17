# -*- coding: utf-8 -*-
{
    'name': "Payroll enterprise income tax (EC Private)",
    'version': '1.0',
    'summary': """Module to incorporate the calculation of income tax for odoo enterprise.""",

    'description': """
        Module to incorporate the calculation of income tax to the payroll for odoo enterprise 
        to the Ecuadorian location. Incorporates information for the private sector of Ecuador.
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
            'hr_dr_payroll_enterprise_income_tax',
            'hr_dr_payroll_enterprise_ec_private'
        ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',

        'data/hr_salary_rule.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
