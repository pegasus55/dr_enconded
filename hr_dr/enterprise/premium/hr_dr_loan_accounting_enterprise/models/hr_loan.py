# -*- coding: utf-8 -*-
import time
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrLoan(models.Model):
    _inherit = 'hr.loan'

    @api.onchange('company_id')
    def on_change_company_id(self):
        if self.company_id:
            self.credit_account_account_id = self.company_id.credit_account_account_loan.id
            self.debit_account_account_id = self.company_id.debit_account_account_loan.id
            self.account_journal_id = self.company_id.account_journal_loan.id
            self.account_analytic_account_id = self.company_id.account_analytic_account_loan.id

    @api.model
    def get_credit_account_account_id(self):
        return self.company_id.credit_account_account_loan.id

    @api.model
    def get_debit_account_account_id(self):
        return self.company_id.debit_account_account_loan.id

    @api.model
    def get_account_journal_id(self):
        return self.company_id.account_journal_loan.id

    @api.model
    def get_account_analytic_account_id(self):
        return self.company_id.account_analytic_account_loan.id

    def crete_account_move(self):
        if not self.credit_account_account_id or not self.debit_account_account_id or not self.account_journal_id:
            raise UserError(_("You must enter the debit account, credit account "
                              "and journal in order to approve the request."))
        if not self.loan_lines:
            raise UserError(_('You must calculate the installments of the loan request before approving it.'))
        time_now = time.strftime('%Y-%m-%d')
        for loan in self:
            amount = loan.loan_amount
            loan_name = loan.employee_requests_id.name
            reference = loan.name
            account_journal_id = loan.account_journal_id.id if loan.account_journal_id else ''
            analytic_account_id = loan.account_analytic_account_id.id if loan.account_analytic_account_id else ''
            debit_account_id = loan.debit_account_account_id.id
            credit_account_id = loan.credit_account_account_id.id

            name = "Préstamo para {}.".format(loan_name)
            credit_vals = {
                'name': name,
                'account_id': credit_account_id,
                'journal_id': account_journal_id,
                'date': time_now,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'loan_id': loan.id,
                'partner_id': loan.employee_requests_id.address_home_id.id,
                # 'analytic_distribution': analytic_account_id,
            }
            line_ids = []
            line_ids.append((0, 0, credit_vals))

            total_installment = len(loan.loan_lines)
            for line in loan.loan_lines:
                name = "Préstamo para {}. Cuota {} de {}".format(loan_name, line.installment, total_installment)

                debit_vals = {
                    'name': name,
                    'account_id': debit_account_id,
                    'journal_id': account_journal_id,
                    'date': line.date,
                    'debit': line.amount,
                    'credit': 0,
                    'loan_id': loan.id,
                    'partner_id': loan.employee_requests_id.address_home_id.id,
                    # 'analytic_distribution': analytic_account_id,
                }
                line_ids.append((0, 0, debit_vals))

            vals = {
                'name': 'Préstamo para' + ' ' + loan_name,
                'narration': loan_name,
                'ref': reference,
                'journal_id': account_journal_id,
                'date': time_now,
                'line_ids': line_ids
            }
            move = self.env['account.move'].create(vals)
            move.action_post()

    def mark_as_approved(self):
        super(HrLoan, self).mark_as_approved()
        self.crete_account_move()

    def mark_as_approved_direct(self):
        super(HrLoan, self).mark_as_approved_direct()
        self.crete_account_move()

    credit_account_account_id = fields.Many2one('account.account', string="Credit account",
                                                default=get_credit_account_account_id)
    debit_account_account_id = fields.Many2one('account.account', string="Debit account",
                                               default=get_debit_account_account_id)
    account_journal_id = fields.Many2one('account.journal', string="Journal", default=get_account_journal_id)
    account_analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic account',
                                                  default=get_account_analytic_account_id)