from odoo import api, fields, models, _


class RegisterAccountPayment(models.TransientModel):
    _name = "register.account.payment"
    _description = "Register account payment"

    account_journal = fields.Many2one('account.journal', string='Account journal for payment',
                                      help="Do not specify anything to take the journal based "
                                           "on the company's configuration")

    pay_living_wage = fields.Many2one('pay.living.wage', string='Pay living wage',
                                      default=lambda self: self._context.get('active_id'))

    def action_register_account_payment(self):
        self.pay_living_wage.generate_payments(self.account_journal)