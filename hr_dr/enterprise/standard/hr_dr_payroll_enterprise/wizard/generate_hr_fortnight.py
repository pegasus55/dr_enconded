from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class GenerateFortnight(models.TransientModel):
    _inherit = "generate.hr.fortnight"

    def create_account_move(self, lines):
        obj_account_move = self.env['account.move']
        journal_id = self.company_id.fortnight_journal
        account_move_data = {
            'ref': 'Fortnight of %s' % str(self.date.strftime("%B/%Y")),
            'journal_id': journal_id.id,
            'date': self.date,
            'move_type': 'entry',
            'company_id': self.env.company.id,
            'line_ids': lines
        }
        if lines:
            obj_account_move.create(account_move_data)

    def generate_account_move_line(self, employee, lines, fortnight):
        account_debit_id = self.company_id.fortnight_payment_account
        if not account_debit_id:
            raise ValidationError(_("You must configure the account for fortnight payment "
                                    "in the company's configuration."))
        credit_account_id = self.company_id.payroll_payment_account
        if not credit_account_id:
            raise ValidationError(_("You must configure the account for payroll payment "
                                    "in the company's configuration."))

        name = _('Fortnight of %s for the collaborator %s') % (
            str(self.date.strftime("%B/%Y")), employee.name
        )
        base_line = {
            'credit': 0.00,
            'debit': 0.00,
            'date': self.date,
            'name': name,
        }
        lines.append((0, 0, {
            **base_line,
            'account_id': account_debit_id.id,
            'debit': fortnight,
        }))
        lines.append((0, 0, {
            **base_line,
            'account_id': credit_account_id.id,
            'credit': fortnight,
            'partner_id': employee.address_home_id.id,
        }))
        return lines

    def create_payment(self, employee, amount):
        account_debit_id = self.company_id.fortnight_payment_account
        if not account_debit_id:
            raise ValidationError(_("You must set up the fortnight payment account in the company."))

        obj_payment = self.env['account.payment']
        obj_payment_method_line = self.env['account.payment.method.line']

        journal_id = False
        if self.account_journal:
            journal_id = self.account_journal
        else:
            if self.company_id.payroll_mode == "01":
                journal_id = self.company_id.main_account_journal
            else:
                for account_journal in self.company_id.account_journal_ids:
                    if account_journal.bank_account_id.bank_id == employee.bank_account_id.bank_id:
                        journal_id = account_journal
        if not journal_id:
            raise ValidationError(_("You must configure the accounting journal for payroll payments "
                                    "in the company configuration. Review the collaborator's bank account: %s.") %
                                  employee.name)

        method_line = obj_payment_method_line.search([
            ('code', '=', 'check'),
            ('payment_type', '=', 'outbound'),
            ('journal_id', '=', journal_id.id),
        ], limit=1)
        bank = employee.bank_account_id.id if employee.bank_account_id else None
        if bank:
            method_line = obj_payment_method_line.search([
                ('code', '=', 'transfer'),
                ('payment_type', '=', 'outbound'),
                ('journal_id', '=', journal_id.id),
            ], limit=1)
        if not method_line:
            method_line = obj_payment_method_line.search([
                ('code', '=', 'manual'),
                ('payment_type', '=', 'outbound'),
                ('journal_id', '=', journal_id.id),
            ], limit=1)

        ref = _('Fortnight of %s for the collaborator %s') % (
            str(self.date.strftime("%B/%Y")), employee.name,
        )

        account_payment = obj_payment.create({
            'partner_type': 'supplier',
            'is_internal_transfer': False,
            'partner_id': False,
            'employee_id': employee.address_home_id.id,
            'amount': amount,
            'date': self.date,
            'ref': ref,
            'payment_type': 'outbound',
            'payroll_payment': True,
            'journal_id': journal_id.id,
            # 'destination_account_id': account_debit_id.id,
            'payment_method_line_id': method_line.id,
            'partner_bank_id': bank,
            'company_id': self.env.company.id,
        })
        account_payment.partner_type = 'supplier'

    account_journal = fields.Many2one('account.journal', string='Account journal for payment',
                                      help="Do not specify anything to take the journal based "
                                           "on the company's configuration")