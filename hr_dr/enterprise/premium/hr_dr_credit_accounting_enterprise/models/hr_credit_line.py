# -*- coding: utf-8 -*-
import time
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class HrCreditLine(models.Model):
    _inherit = "hr.credit.line"
    
    def action_paid_amount(self):
        """This create the account move line for payment of each installment.
            """
        timenow = time.strftime('%Y-%m-%d')
        for line in self:
            if line.employee_credit_id.state != 'in_payroll':
                raise UserError(_("Employee credit request must be in payroll."))
            amount = line.amount

            credit_name = line.employee_id.name
            reference = line.employee_credit_id.name
            journal_id = line.employee_credit_id.journal_id.id
            debit_account_id = line.employee_credit_id.emp_account_id.id
            credit_account_id = line.employee_credit_id.treasury_account_id.id
            debit_vals = {
                'name': credit_name,
                'account_id': debit_account_id,
                'journal_id': journal_id,
                'date': timenow,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
            }
            credit_vals = {
                'name': credit_name,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'date': timenow,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
            }
            vals = {
                'name': 'Crédito empleado: ' + credit_name,
                'narration': credit_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': timenow,
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }
            move = self.env['account.move'].create(vals)
            move.post()
        return True