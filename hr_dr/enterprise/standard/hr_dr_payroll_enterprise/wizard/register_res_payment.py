from odoo import api, fields, models, _


class RegisterResPayment(models.TransientModel):
    _name = "register.res.payment"
    _description = "Register retired collaborator salary payment"

    account_journal = fields.Many2one('account.journal', string='Account journal for payment',
                                      help="Do not specify anything to take the journal based "
                                           "on the company's configuration")

    retired_employee_salary = fields.Many2one('retired.employee.salary', string='Retired collaborator salary',
                                              default=lambda self: self._context.get('active_id'))

    def action_register_account_payment(self):
        self.retired_employee_salary.generate_payments(self.account_journal)