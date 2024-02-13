from odoo import api, fields, models, _


class EmployeeSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    _SM = [
        ('without_signature', _('Without signature')),
        ('uploaded_image', _('Uploaded image')),
        ('electronic_signature', _('Electronic signature')),
    ]
    employee_certificates_signature_mode = fields.Selection(_SM, string='Signature mode for work certificates',
                                                            required=True)
    _INCOME_BASED_ON = [
        ('salary', _('Salary')),
        ('payroll', _('Payroll')),
    ]
    certificate_with_income_based_on = fields.Selection(_INCOME_BASED_ON, required=True,
                                                        string='Certificate with income based on', help='')
    _PAYROLL_ANALYZE = [
        ('last_three_payrolls', _('Last three payrolls')),
        ('last_six_payrolls', _('Last six payrolls')),
        ('last_nine_payrolls', _('Last nine payrolls')),
        ('last_twelve_payrolls', _('Last twelve payrolls')),
        ('all_payroll', _('All payroll')),
    ]
    payroll_to_analyze = fields.Selection(_PAYROLL_ANALYZE, string='Payroll to analyze', help='')
    salary_rule_code = fields.Char(string='Salary rule code')

    @api.model
    def get_values(self):
        res = super(EmployeeSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()
        res.update(employee_certificates_signature_mode=config_parameter.
                   get_param('employee.certificates.signature.mode', default=''))
        res.update(certificate_with_income_based_on=config_parameter.
                   get_param('certificate.with.income.based_on', default=''))
        res.update(payroll_to_analyze=config_parameter.
                   get_param('certificate.payroll.to.analyze', default=''))
        res.update(salary_rule_code=config_parameter.
                   get_param('certificate.salary.rule.code.to.analyze', default=''))
        return res

    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param("employee.certificates.signature.mode", self.employee_certificates_signature_mode)
        set_param("certificate.with.income.based_on", self.certificate_with_income_based_on)
        set_param("certificate.payroll.to.analyze", self.payroll_to_analyze)
        set_param("certificate.salary.rule.code.to.analyze", self.salary_rule_code)
        super(EmployeeSettings, self).set_values()