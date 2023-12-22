# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Company(models.Model):
    _inherit = 'res.company'

    credit_account_account_loan = fields.Many2one('account.account', string='Default credit account')
    debit_account_account_loan = fields.Many2one('account.account', string='Default debit account')
    account_analytic_account_loan = fields.Many2one('account.analytic.account', string='Default analytic account')
    account_journal_loan = fields.Many2one('account.journal', string='Default journal')