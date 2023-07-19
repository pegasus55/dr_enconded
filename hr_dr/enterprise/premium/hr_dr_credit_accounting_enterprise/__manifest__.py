# -*- coding: utf-8 -*-
{
    'name': 'Contabilidad Crédito Empleados',
    'version': '1.0.0',
    'summary': 'Contabilidad Crédito Empleados',
    'description': """
        Incorpora las entradas contables a los créditos de los empleados.
        """,
    'category': 'Generic Modules/Human Resources',
    'author': "Dainovy Rodriguez Marrero",
    'company': 'Dainovy Rodriguez Marrero',
    'maintainer': 'Dainovy Rodriguez Marrero',
    'website': "https://www.drm.com",
    'depends': [
        'base', 'dr_start_system', 'hr_payroll', 'hr', 'account', 'hr_dr_employee_credit',
    ],
    'data': [
        'views/res_config_settings.xml',
        'views/hr_credit_acc.xml',

        'data/parameter.xml',

    ],
    'demo': [],
    'images': ["static/description/icon.png"],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
