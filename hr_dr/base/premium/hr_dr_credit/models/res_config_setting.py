from odoo import api, fields, models, _


class EmployeeCreditSettings(models.TransientModel):
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
    employee_credit_request_notifications_mode = fields.Selection(
        _NOTIFICATIONS, string='Credit request notifications mode', help='')
    employee_credit_request_administrator = fields.Many2one(
        'hr.employee',
        string='Credit request administrator',
        help='')
    employee_credit_request_second_administrator = fields.Many2one(
        'hr.employee',
        string='Credit request second administrator',
        help='')
    credit_maximum_number_of_installments = fields.Integer(string="Maximum number of installments")
    maximum_number_of_credits = fields.Integer(string="Maximum number of credits")
    _SM = [
        ('without_signature', _('Without signature')),
        ('uploaded_image', _('Uploaded image')),
        ('electronic_signature', _('Electronic signature')),
    ]
    credits_signature_mode = fields.Selection(_SM, string='Signature mode for credits', required=True)
    maximum_credit_percentage = fields.Float(string="Maximum percentage of indebtedness")
    _INDEBTEDNESS = [
        ('salary', _('Salary')),
        ('payroll', _('Payroll')),
    ]
    maximum_credit_percentage_based_on = fields.Selection(_INDEBTEDNESS, required=True,
                                                          string='Maximum percentage of indebtedness based on', help='')
    _PAYROLL_ANALYZE = [
        ('last_three_payrolls', _('Last three payrolls')),
        ('last_six_payrolls', _('Last six payrolls')),
        ('last_nine_payrolls', _('Last nine payrolls')),
        ('last_twelve_payrolls', _('Last twelve payrolls')),
        ('all_payroll', _('All payroll')),
    ]
    credit_payroll_to_analyze = fields.Selection(_PAYROLL_ANALYZE, string='Payroll to analyze', help='')
    credit_salary_rule_code = fields.Char(string='Salary rule code')
    credit_months_in_the_company = fields.Integer(
        string="Minimum number of months in the company to apply for a credit.")

    @api.model
    def get_values(self):
        res = super(EmployeeCreditSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()

        res.update(employee_credit_request_notifications_mode=config_parameter.
                   get_param('employee.credit.request.notifications.mode', default=''))

        if config_parameter.get_param('employee.credit.request.administrator'):
            if config_parameter.get_param('employee.credit.request.administrator') != '':
                res.update(employee_credit_request_administrator=int(
                    config_parameter.get_param('employee.credit.request.administrator')))

        if config_parameter.get_param('employee.credit.request.second.administrator'):
            if config_parameter.get_param('employee.credit.request.second.administrator') != '':
                res.update(employee_credit_request_second_administrator=int(
                    config_parameter.get_param('employee.credit.request.second.administrator')))

        res.update(credit_maximum_number_of_installments=config_parameter.get_param(
            'credit.maximum.number.of.installments', default=6))
        res.update(maximum_number_of_credits=config_parameter.get_param('maximum.number.of.credits', default=1))
        res.update(credits_signature_mode=config_parameter.get_param('credits.signature.mode', default=''))
        res.update(maximum_credit_percentage=config_parameter.get_param('maximum.credit.percentage', default=30))
        res.update(maximum_credit_percentage_based_on=config_parameter.get_param(
            'maximum.credit.percentage.based_on', default=''))
        res.update(credit_payroll_to_analyze=config_parameter.get_param('credit.payroll.to.analyze', default=''))
        res.update(credit_salary_rule_code=config_parameter.
                   get_param('credit.salary.rule.code.to.analyze', default=''))
        res.update(credit_months_in_the_company=config_parameter.get_param('credit.months.in.the.company', default=6))

        return res

    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param

        set_param("employee.credit.request.notifications.mode", self.employee_credit_request_notifications_mode)
        set_param("employee.credit.request.administrator", self.employee_credit_request_administrator.id)
        set_param("employee.credit.request.second.administrator", self.employee_credit_request_second_administrator.id)
        set_param('credit.maximum.number.of.installments', self.credit_maximum_number_of_installments)
        set_param('maximum.number.of.credits', self.maximum_number_of_credits)
        set_param("credits.signature.mode", self.credits_signature_mode)
        set_param('maximum.credit.percentage', self.maximum_credit_percentage)
        set_param("maximum.credit.percentage.based_on", self.maximum_credit_percentage_based_on)
        set_param("credit.payroll.to.analyze", self.credit_payroll_to_analyze)
        set_param("credit.salary.rule.code.to.analyze", self.credit_salary_rule_code)
        set_param('credit.months.in.the.company', self.credit_months_in_the_company)
        super(EmployeeCreditSettings, self).set_values()

    @api.onchange('employee_credit_request_notifications_mode')
    def _onchange_employee_credit_request_notifications_mode(self):
        if self.employee_credit_request_notifications_mode == "Without_notifications" \
                or self.employee_credit_request_notifications_mode == "One_level_bd" \
                or self.employee_credit_request_notifications_mode == "One_level_br" \
                or self.employee_credit_request_notifications_mode == "One_level_bc"\
                or self.employee_credit_request_notifications_mode == "Two_levels_bd"\
                or self.employee_credit_request_notifications_mode == "All_levels_bd"\
                or self.employee_credit_request_notifications_mode == "Personalized":
            self.employee_credit_request_administrator = ""

        if self.employee_credit_request_notifications_mode != "One_level_bd_and_two_administrator":
            self.employee_credit_request_second_administrator = ""

    @api.onchange('maximum_credit_percentage_based_on')
    def _onchange_maximum_credit_percentage_based_on(self):
        if self.maximum_credit_percentage_based_on == "salary":
            self.credit_payroll_to_analyze = ""