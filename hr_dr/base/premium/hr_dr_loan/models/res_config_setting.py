from odoo import api, fields, models, _


class LoanSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    _NOTIFICATIONS = [
        ('Without_notifications', _('Without notifications')),

        ('Administrator', _('Administrator')),

        ('One_level_bd', _('One level based on department')),
        ('One_level_br', _('One level based on responsible')),
        ('One_level_bc', _('One level based on coach')),

        ('One_level_bd_and_administrator', _('One level based on department and administrator')),
        ('One_level_br_and_administrator', _('One level based on responsible and administrator')),
        ('One_level_bc_and_administrator', _('One level based on coach and administrator')),

        ('One_level_bd_and_two_administrator', _('One level based on department and two administrator')),

        ('Two_levels_bd', _('Two levels based on department')),
        ('Two_levels_bd_and_administrator', _('Two levels based on department and administrator')),

        ('All_levels_bd', _('All levels based on department')),
        ('All_levels_bd_and_administrator', _('All levels based on department and administrator')),

        ('Personalized', _('Personalized'))
    ]
    loan_request_notifications_mode = fields.Selection(_NOTIFICATIONS, string='Loan request notifications mode')
    loan_request_administrator = fields.Many2one('hr.employee', string='Loan request administrator')
    loan_request_second_administrator = fields.Many2one('hr.employee', string='Loan request second administrator')
    maximum_number_of_installments = fields.Integer(string="Maximum number of installments")
    maximum_number_of_loans = fields.Integer(string="Maximum number of loans")
    _SM = [
        ('without_signature', _('Without signature')),
        ('uploaded_image', _('Uploaded image')),
        ('electronic_signature', _('Electronic signature')),
    ]
    loans_signature_mode = fields.Selection(_SM, string='Signature mode for loans', required=True)
    maximum_loan_percentage = fields.Float(string="Maximum percentage of indebtedness")
    _INDEBTEDNESS = [
        ('salary', _('Salary')),
        ('payroll', _('Payroll')),
    ]
    maximum_loan_percentage_based_on = fields.Selection(_INDEBTEDNESS, required=True,
                                                        string='Maximum percentage of indebtedness based on')
    _PAYROLL_ANALYZE = [
        ('last_three_payrolls', _('Last three payrolls')),
        ('last_six_payrolls', _('Last six payrolls')),
        ('last_nine_payrolls', _('Last nine payrolls')),
        ('last_twelve_payrolls', _('Last twelve payrolls')),
        ('all_payroll', _('All payroll')),
    ]
    loan_payroll_to_analyze = fields.Selection(_PAYROLL_ANALYZE, string='Payroll to analyze', help='')
    loan_salary_rule_code = fields.Char(string='Salary rule code')
    loan_months_in_the_company = fields.Integer(string="Minimum number of months in the company to apply for a loan")
    
    @api.model
    def get_values(self):
        res = super(LoanSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()

        res.update(loan_request_notifications_mode=config_parameter.
                   get_param('loan.request.notifications.mode', default=''))

        if config_parameter.get_param('loan.request.administrator'):
            if config_parameter.get_param('loan.request.administrator') != '':
                res.update(loan_request_administrator=int(
                    config_parameter.get_param('loan.request.administrator')))

        if config_parameter.get_param('loan.request.second.administrator'):
            if config_parameter.get_param('loan.request.second.administrator') != '':
                res.update(loan_request_second_administrator=int(
                    config_parameter.get_param('loan.request.second.administrator')))

        res.update(maximum_number_of_installments=config_parameter.
                   get_param('maximum.number.of.installments', default=6))
        res.update(maximum_number_of_loans=config_parameter.get_param('maximum.number.of.loans', default=1))
        res.update(loans_signature_mode=config_parameter.get_param('loans.signature.mode', default=''))
        res.update(maximum_loan_percentage=config_parameter.get_param('maximum.loan.percentage', default=30))
        res.update(maximum_loan_percentage_based_on=config_parameter.
                   get_param('maximum.loan.percentage.based_on', default=''))
        res.update(loan_payroll_to_analyze=config_parameter.get_param('loan.payroll.to.analyze', default=''))
        res.update(loan_salary_rule_code=config_parameter.
                   get_param('loan.salary.rule.code.to.analyze', default=''))
        res.update(loan_months_in_the_company=config_parameter.get_param('loan.months.in.the.company', default=6))

        return res
    
    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param

        set_param("loan.request.notifications.mode", self.loan_request_notifications_mode)
        set_param("loan.request.administrator", self.loan_request_administrator.id)
        set_param("loan.request.second.administrator", self.loan_request_second_administrator.id)
        set_param('maximum.number.of.installments', self.maximum_number_of_installments)
        set_param('maximum.number.of.loans', self.maximum_number_of_loans)
        set_param("loans.signature.mode", self.loans_signature_mode)
        set_param('maximum.loan.percentage', self.maximum_loan_percentage)
        set_param("maximum.loan.percentage.based_on", self.maximum_loan_percentage_based_on)
        set_param("loan.payroll.to.analyze", self.loan_payroll_to_analyze)
        set_param("loan.salary.rule.code.to.analyze", self.loan_salary_rule_code)
        set_param('loan.months.in.the.company', self.loan_months_in_the_company)

        super(LoanSettings, self).set_values()

    @api.onchange('loan_request_notifications_mode')
    def _onchange_loan_request_notifications_mode(self):
        if self.loan_request_notifications_mode == "Without_notifications" \
                or self.loan_request_notifications_mode == "One_level_bd" \
                or self.loan_request_notifications_mode == "One_level_br" \
                or self.loan_request_notifications_mode == "One_level_bc"\
                or self.loan_request_notifications_mode == "Two_levels_bd"\
                or self.loan_request_notifications_mode == "All_levels_bd"\
                or self.loan_request_notifications_mode == "Personalized":
            self.loan_request_administrator = ""
        if self.loan_request_notifications_mode != "One_level_bd_and_two_administrator":
            self.loan_request_second_administrator = ""

    @api.onchange('maximum_loan_percentage_based_on')
    def _onchange_maximum_loan_percentage_based_on(self):
        if self.maximum_loan_percentage_based_on == "salary":
            self.loan_payroll_to_analyze = ""