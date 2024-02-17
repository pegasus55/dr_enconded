# -*- coding: utf-8 -*-
{
    'name': "Electronic Signature",

    'summary': """
        Add electronic signature to generated PDF documents. """,

    'description': """
        Allow digitally signing a rendered PDF document with a P12 certificate.
    """,

    'author': "Nukleo Solutions",
    'website': "https://www.nukleosolutions.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'hr_dr_employee'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee.xml',
        'wizards/request_passphrase_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dr_signature/static/src/js/action_service.js',
        ],
    },
    'external_dependencies': {'python': ['pyhanko']},
    'license': 'AGPL-3',
}
