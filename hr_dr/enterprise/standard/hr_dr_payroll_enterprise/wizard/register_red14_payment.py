from odoo import api, fields, models, _


class RegisterRed14Payment(models.TransientModel):
    _name = "register.red14.payment"
    _description = "Register retired collaborator fourteenth salary payment"

    account_journal = fields.Many2one('account.journal', string='Account journal for payment',
                                      help="Do not specify anything to take the journal based "
                                           "on the company's configuration")

    retired_employee_fourteenth_salary = fields.Many2one('retired.employee.fourteenth.salary',
                                                         string='Retired collaborator fourteenth salary',
                                                         default=lambda self: self._context.get('active_id'))

    def action_register_account_payment(self):
        self.retired_employee_fourteenth_salary.generate_payments(self.account_journal)