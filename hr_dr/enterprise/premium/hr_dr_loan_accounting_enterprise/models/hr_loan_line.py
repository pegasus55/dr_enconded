# -*- coding: utf-8 -*-
import time
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrLoanLine(models.Model):
    _inherit = "hr.loan.line"
    
    def action_paid_amount(self):
        """This create the account move line for payment of each installment.
            """
        time_now = time.strftime('%Y-%m-%d')
        for line in self:
            if line.loan_id.state != 'approved':
                raise UserError(_("Loan request must be approved."))
            amount = line.amount
            loan_name = line.employee_id.name
            reference = line.loan_id.name
            account_journal_id = line.loan_id.account_journal_id.id
            debit_account_id = line.loan_id.credit_account_account_id.id
            credit_account_id = line.loan_id.debit_account_account_id.id
            debit_vals = {
                'name': loan_name,
                'account_id': debit_account_id,
                'journal_id': account_journal_id,
                'date': time_now,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
            }
            credit_vals = {
                'name': loan_name,
                'account_id': credit_account_id,
                'journal_id': account_journal_id,
                'date': time_now,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
            }
            vals = {
                'name': 'Préstamo para' + ' ' + loan_name,
                'narration': loan_name,
                'ref': reference,
                'journal_id': account_journal_id,
                'date': time_now,
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }
            move = self.env['account.move'].create(vals)
            move.action_post()
        return True