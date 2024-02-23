from odoo import api, fields, models, _


class RegisterRed13Payment(models.TransientModel):
    _name = "register.red13.payment"
    _description = "Register retired collaborator thirteenth salary payment"

    account_journal = fields.Many2one('account.journal', string='Account journal for payment',
                                      help="Do not specify anything to take the journal based "
                                           "on the company's configuration")

    retired_employee_thirteenth_salary = fields.Many2one('retired.employee.thirteenth.salary',
                                                         string='Retired collaborator thirteenth salary',
                                                         default=lambda self: self._context.get('active_id'))

    def action_register_account_payment(self):
        self.retired_employee_thirteenth_salary.generate_payments(self.account_journal)