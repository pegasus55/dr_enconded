# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Company(models.Model):
    _inherit = 'res.company'

    _PAYROLL_MODE = [
        ('01', 'An accounting journal'),
        ('02', 'Multiple accounting journals'),
    ]
    _A_E_BASED_ON = [
        ('01', 'Salary rule ledger accounts'),
        ('02', 'Company settings'),
    ]

    payroll_mode = fields.Selection(_PAYROLL_MODE, string='Payroll mode', default='02', required=True)
    main_account_journal = fields.Many2one('account.journal', 'Main account journal', required=True)
    account_journal_ids = fields.Many2many('account.journal', 'rcs_account_journal_rel', 'res_config_settings_id',
                                           'account_journal_id', string='Account journals')

    fortnight_journal = fields.Many2one('account.journal', string='Fortnight journal')
    fortnight_payment_account = fields.Many2one('account.account', string='Fortnight payment account')

    payroll_journal = fields.Many2one('account.journal', string='Payroll journal')
    payroll_payment_account = fields.Many2one('account.account', string='Payroll payment account')

    # D14
    journal_fourteenth_id = fields.Many2one('account.journal', string='Account journal',
                                            help='Journal used for the annual settlement entries '
                                                 'of the fourteenth salary.')
    xiv_adjust_account = fields.Many2one('account.account', string='Tenth adjustment account',
                                         help='Account for the differences between what was provisioned '
                                              'and what was calculated when paying the fourteenth salary annually.')
    xiv_provision_account = fields.Many2one('account.account', string='Provision account',
                                            help='Account to compute and settle the provisions for the annual payment '
                                                 'of the fourteenth salary.')
    xiv_judicial_withholding_account = fields.Many2one('account.account', string='Account for judicial withholding',
                                                       help='Account to settle judicial withholding in the annual '
                                                            'payment of the fourteenth salary.')
    xiv_advance_account = fields.Many2one('account.account', string='Account for advance',
                                          help='Account to settle the advances delivered on the fourteenth salary, '
                                               'for the annual payment of the fourteenth salary.')
    xiv_payable_account = fields.Many2one('account.account', string='Payable account',
                                          help='Account payable upon settlement of the fourteenth salary.')

    # D13
    journal_thirteenth_id = fields.Many2one('account.journal', string='Account journal',
                                            help='Journal used for annual settlement entries of the thirteenth salary.')
    xiii_adjust_account = fields.Many2one('account.account', string='Tenth adjustment account',
                                          help='Account for the differences between what was provisioned '
                                               'and what was calculated when paying the thirteenth salary annually.')
    xiii_provision_account = fields.Many2one('account.account', string='Provision account',
                                             help='Account to compute and settle the provisions for the annual payment '
                                                  'of the thirteenth salary.')
    xiii_judicial_withholding_account = fields.Many2one('account.account', string='Account for judicial withholding',
                                                        help='Account to settle judicial withholding in the annual '
                                                             'payment of the thirteenth salary.')
    xiii_advance_account = fields.Many2one('account.account', string='Account for advance',
                                           help='Account to settle the advances delivered on the thirteenth salary, '
                                                'for the annual payment of the thirteenth salary.')
    xiii_payable_account = fields.Many2one('account.account', string='Payable account',
                                           help='Account payable upon settlement of the thirteenth salary.')

    # Retired employee salary
    re_salary_accounting_entries_based = fields.Selection(_A_E_BASED_ON, string='Accounting entries based on',
                                                          default='02', required=True)
    re_salary_salary_rule_code = fields.Char(string="Salary rule code")
    re_salary_credit_account = fields.Many2one('account.account', string="Credit account", ondelete='restrict')
    re_salary_debit_account = fields.Many2one('account.account', string="Debit account", ondelete='restrict')
    re_salary_journal = fields.Many2one('account.journal', string="Account journal", ondelete='restrict')
    re_salary_account_analytic_account = fields.Many2one('account.analytic.account',
                                                         string="Account analytic account", ondelete='restrict')

    # Retired employee D13 salary
    red13_salary_accounting_entries_based = fields.Selection(_A_E_BASED_ON, string='Accounting entries based on',
                                                             default='02', required=True)
    red13_salary_salary_rule_code = fields.Char(string="Salary rule code")
    red13_salary_credit_account = fields.Many2one('account.account', string="Credit account", ondelete='restrict')
    red13_salary_debit_account = fields.Many2one('account.account', string="Debit account", ondelete='restrict')
    red13_salary_journal = fields.Many2one('account.journal', string="Account journal", ondelete='restrict')
    red13_salary_account_analytic_account = fields.Many2one('account.analytic.account',
                                                            string="Account analytic account", ondelete='restrict')

    # Retired employee D14 salary
    red14_salary_accounting_entries_based = fields.Selection(_A_E_BASED_ON, string='Accounting entries based on',
                                                             default='02', required=True)
    red14_salary_salary_rule_code = fields.Char(string="Salary rule code")
    red14_salary_credit_account = fields.Many2one('account.account', string="Credit account", ondelete='restrict')
    red14_salary_debit_account = fields.Many2one('account.account', string="Debit account", ondelete='restrict')
    red14_salary_journal = fields.Many2one('account.journal', string="Account journal", ondelete='restrict')
    red14_salary_account_analytic_account = fields.Many2one('account.analytic.account',
                                                            string="Account analytic account", ondelete='restrict')

    # Utility
    utility_accounting_entries_based = fields.Selection(_A_E_BASED_ON, string='Accounting entries based on',
                                                        default='02', required=True)
    utility_salary_rule_code = fields.Char(string="Salary rule code")
    payment_utility_credit_account = fields.Many2one('account.account', string="Credit account", ondelete='restrict')
    payment_utility_debit_account = fields.Many2one('account.account', string="Debit account", ondelete='restrict')
    payment_utility_journal = fields.Many2one('account.journal', string="Account journal", ondelete='restrict')
    payment_utility_account_analytic_account = fields.Many2one('account.analytic.account',
                                                               string="Account analytic account",
                                                               ondelete='restrict')
    utility_advance_account = fields.Many2one('account.account', string='Account for advance')
    utility_judicial_withholding_account = fields.Many2one('account.account',
                                                           string='Account for judicial withholding', help='')

    # Living wage
    living_wage_accounting_entries_based = fields.Selection(_A_E_BASED_ON, string='Accounting entries based on',
                                                            default='02', required=True)
    living_wage_salary_rule_code = fields.Char(string="Salary rule code")
    pay_living_wage_credit_account = fields.Many2one('account.account', string="Credit account", ondelete='restrict')
    pay_living_wage_debit_account = fields.Many2one('account.account', string="Debit account", ondelete='restrict')
    pay_living_wage_journal = fields.Many2one('account.journal', string="Account journal", ondelete='restrict')
    pay_living_wage_account_analytic_account = fields.Many2one('account.analytic.account',
                                                               string="Account analytic account",
                                                               ondelete='restrict')

    rdep_exclude_dif_less_than = fields.Float(
        string='Omitir diferencia menor a',
        default=0.12,
        help='En el RDEP se omiten las diferencias entre el decimo cuarto y el valor calculado con un rango +/- a este valor.'
    )
    # required_personal_expenses = fields.Selection(
    #     [('required', 'Requiere gastos personales'),
    #      ('without_control', 'Sin control')],
    #     string='Control gastos personales',
    #     default='required',
    #     track_visibility='onchange',
    #     help='Bloquea la generación de nomina de no existir gastos personales.')
    # xiv_exclude_dif_less_than = fields.Float(
    #     string='Omitir diferencia menor a',
    #     default=0.0,
    #     help='Se omiten las diferencias menores o iguales a este monto para el calculo del decimo cuarto sueldo'
    #     )
    # xiii_exclude_dif_less_than = fields.Float(
    #     string='Omitir diferencia menor a',
    #     default=0.1,
    #     help='Se omiten las diferencias menores o iguales a este monto para el calculo del decimo cuarto sueldo'
    #     )

