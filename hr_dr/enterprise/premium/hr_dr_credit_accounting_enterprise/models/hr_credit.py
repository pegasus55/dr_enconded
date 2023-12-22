# -*- coding: utf-8 -*-
import time
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class HrCredit(models.Model):
    _inherit = 'hr.credit'

    @api.onchange('company_id')
    def on_change_company_id(self):
        if self.company_id:
            self.credit_account_account_id = self.company_id.credit_account_account_credit.id
            self.debit_account_account_id = self.company_id.debit_account_account_credit.id
            self.account_journal_id = self.company_id.account_journal_credit.id
            self.account_analytic_account_id = self.company_id.account_analytic_account_credit.id

    @api.model
    def get_credit_account_account_id(self):
        return self.company_id.credit_account_account_credit.id

    @api.model
    def get_debit_account_account_id(self):
        return self.company_id.debit_account_account_credit.id

    @api.model
    def get_account_journal_id(self):
        return self.company_id.account_journal_credit.id

    @api.model
    def get_account_analytic_account_id(self):
        return self.company_id.account_analytic_account_credit.id

    def go_to_payroll(self):
        if not self.invoice:
            raise UserError(_("You must enter the invoice."))
        if not self.credit_account_account_id or not self.debit_account_account_id or not self.account_journal_id:
            raise UserError(_("You must enter debit account, credit account and journal for go to payroll."))
        if not self.credit_lines:
            raise UserError(_('You must calculate the credit request fees before going to payroll.'))

        result = super(HrCredit, self).go_to_payroll()

        timenow = time.strftime('%Y-%m-%d')
        for credit in self:
            amount = credit.credit_amount
            credit_name = credit.employee_id.name + ' ' + credit.invoice
            reference = credit.name + ' ' + credit.invoice
            journal_id = credit.account_journal_id.id if credit.account_journal_id else ''
            analytic_account_id = credit.account_analytic_account_id.id if credit.account_analytic_account_id else ''
            debit_account_id = credit.debit_account_account_id.id
            credit_account_id = credit.credit_account_account_id.id

            name = "Crédito directo: {}".format(credit_name)
            credit_vals = {
                'name': name,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'date': timenow,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'employee_credit_id': credit.id,
                'partner_id': credit.employee_id.address_home_id.id,
                'analytic_account_id': analytic_account_id,
            }
            line_ids = []
            line_ids.append((0, 0, credit_vals))

            total_installment = len(credit.credit_lines)
            for line in credit.credit_lines:
                name = "Crédito directo: {}. Factura: {}. Cuota {} de {}".format(credit_name, credit.invoice, line.installment, total_installment)

                debit_vals = {
                    'name': name,
                    'account_id': debit_account_id,
                    'journal_id': journal_id,
                    'date': line.date,
                    'debit': line.amount,
                    'credit': 0,
                    'employee_credit_id': credit.id,
                    'partner_id': credit.employee_id.address_home_id.id,
                    'analytic_account_id': analytic_account_id,
                }
                line_ids.append((0, 0, debit_vals))

            vals = {
                'name': 'Crédito directo: ' + credit_name,
                'narration': credit_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': timenow,
                'line_ids': line_ids
            }
            move = self.env['account.move'].create(vals)
            move.post()

        return result

    invoice = fields.Char(string="Invoice")
    credit_account_account_id = fields.Many2one('account.account', string="Credit account",
                                                default=get_credit_account_account_id)
    debit_account_account_id = fields.Many2one('account.account', string="Debit account",
                                               default=get_debit_account_account_id)
    account_journal_id = fields.Many2one('account.journal', string="Journal", default=get_account_journal_id)
    account_analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic account',
                                                  default=get_account_analytic_account_id)