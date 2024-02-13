from odoo import api, fields, models, _

class EmployeeCreditSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    credit_account = fields.Many2one(
        'account.account',
        'Default credit account',
        help='')
    debit_account = fields.Many2one(
        'account.account',
        'Default debit account',
        help='')
    account_analytic_account = fields.Many2one(
        'account.analytic.account',
        'Default analytic account',
        help='')
    journal = fields.Many2one(
        'account.journal',
        'Default journal',
        help='')
    
    @api.model
    def get_values(self):
        res = super(EmployeeCreditSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()

        if ICPSudo.get_param('eca.default.credit.account'):
            if ICPSudo.get_param('eca.default.credit.account') != '':
                res.update(credit_account=int(
                    ICPSudo.get_param('eca.default.credit.account')))

        if ICPSudo.get_param('eca.default.debit.account'):
            if ICPSudo.get_param('eca.default.debit.account') != '':
                res.update(debit_account=int(
                    ICPSudo.get_param('eca.default.debit.account')))
        #
        if ICPSudo.get_param('eca.default.account.analytic.account'):
            if ICPSudo.get_param('eca.default.account.analytic.account') != '':
                res.update(account_analytic_account=int(
                    ICPSudo.get_param('eca.default.account.analytic.account')))
        #
        if ICPSudo.get_param('eca.default.journal'):
            if ICPSudo.get_param('eca.default.journal') != '':
                res.update(journal=int(
                    ICPSudo.get_param('eca.default.journal')))

        return res
    
    
    def set_values(self):

        set_param = self.env['ir.config_parameter'].sudo().set_param

        set_param("eca.default.credit.account", self.credit_account.id)
        set_param("eca.default.debit.account", self.debit_account.id)
        set_param("eca.default.account.analytic.account", self.account_analytic_account.id)
        set_param("eca.default.journal", self.journal.id)

        super(EmployeeCreditSettings, self).set_values()
