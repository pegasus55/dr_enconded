# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ContractTypeAccountAccount(models.Model):
    _name = 'hr.contract.type.account.account'
    _description = 'Contract type account account'
    _inherit = ['mail.thread']

    salary_rule_id = fields.Many2one('hr.salary.rule', string='Salary rule', tracking=True)
    contract_type_id = fields.Many2one('hr.contract.type', string='Contract type', tracking=True)
    debit_account = fields.Many2one('account.account', string='Debit account', help='', tracking=True)
    credit_account = fields.Many2one('account.account', string='Credit account', help='', tracking=True)
    account_analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic account', tracking=True)
    account_tax_id = fields.Many2one('account.tax', 'Tax', help='', tracking=True)
