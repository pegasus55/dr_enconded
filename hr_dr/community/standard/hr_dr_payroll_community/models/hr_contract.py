# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class Contract(models.Model):
    _inherit = 'hr.contract'

    @api.model
    def default_get(self, fields):
        vals = super(Contract, self).default_get(fields)
        vals.update({
            'struct_id': self.env.ref('hr_dr_payroll_community.payroll_structure_01').id,
        })
        return vals

    @api.model
    def get_account_payable_payroll(self):
        return ''
        payable_payroll = self.env.ref('l10n_ec.1_a201070401', False)
        if payable_payroll:
            payable_payroll = payable_payroll.id
        return payable_payroll

    @api.model
    def get_salary_journal(self):
        return ''
        # journal_wage = self.env.ref('ecua_invoice_type.journal_wage', False)
        # if journal_wage:
        #     journal_wage = journal_wage.id
        # if self.env.user.company_id.journal_wage_id:
        #     journal_wage = self.env.user.company_id.journal_wage_id.id
        # return journal_wage

    @api.model
    def get_analytic_account(self):
        return ''
        # journal_wage = self.env.ref('ecua_invoice_type.journal_wage', False)
        # if journal_wage:
        #     journal_wage = journal_wage.id
        # if self.env.user.company_id.journal_wage_id:
        #     journal_wage = self.env.user.company_id.journal_wage_id.id
        # return journal_wage

    account_payable_payroll = fields.Many2one('account.account', string='Account payable payroll',
                                              default=get_account_payable_payroll, tracking=True, help='')
    journal_id = fields.Many2one('account.journal', string='Salary journal', tracking=True, default=get_salary_journal,
                                 help='')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic account', tracking=True,
                                          default=get_analytic_account)